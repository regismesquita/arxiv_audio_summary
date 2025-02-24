#!/usr/bin/env python3
import os
import json
import requests
import subprocess
from datetime import datetime
import tempfile
import logging
import concurrent.futures
import re
from bs4 import BeautifulSoup

# --- Docling Imports ---
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import ImageRefMode

# --- Kokoro & TTS Imports ---
from kokoro import KPipeline
import soundfile as sf

# --- Flask Imports ---
from flask import Flask, send_file, request, jsonify

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Cache Setup ---
CACHE_DIR = "cache"
ARXIV_CACHE_FILE = os.path.join(CACHE_DIR, "arxiv_list.json")
ARTICLES_CACHE_DIR = os.path.join(CACHE_DIR, "articles")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
    logger.debug("Created cache directory: %s", CACHE_DIR)
if not os.path.exists(ARTICLES_CACHE_DIR):
    os.makedirs(ARTICLES_CACHE_DIR)
    logger.debug("Created articles cache directory: %s", ARTICLES_CACHE_DIR)

# --- Instantiate Docling Converter ---
logger.debug("Instantiating Docling converter with PDF options.")
pdf_options = PdfFormatOption(
    pipeline_options=PdfPipelineOptions(generate_picture_images=True)
)
doc_converter = DocumentConverter(format_options={InputFormat.PDF: pdf_options})

DEFAULT_ARXIV_URL = os.environ.get("ARXIV_URL", "https://arxiv.org/list/cs/new")
DEFAULT_LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:4000/v1/chat/completions")
DEFAULT_MODEL_NAME = os.environ.get("MODEL_NAME", "mistral-small-latest")


# --- Module: Fetcher ---
def fetch_arxiv_list(force_refresh=False, arxiv_url=DEFAULT_ARXIV_URL):
    """
    Fetches the latest CS articles from arXiv. If a cache exists, reads from it
    unless force_refresh is True. Otherwise, parses the arXiv page, extracts
    article metadata, and caches it.
    """
    logger.debug("Checking for cached arXIV list at %s", ARXIV_CACHE_FILE)
    if not force_refresh and os.path.exists(ARXIV_CACHE_FILE):
        logger.info("Cache found for arXiv list. Loading from cache.")
        with open(ARXIV_CACHE_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)
        logger.debug("Loaded %d articles from cache.", len(articles))
        return articles

    url = arxiv_url
    logger.info("Fetching arXiv page from %s", url)
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(
            "Failed to fetch arXiv page. Status code: %d", response.status_code
        )
        raise Exception("Failed to fetch arXiv page.")

    logger.debug("Parsing arXiv HTML content.")
    soup = BeautifulSoup(response.text, "html.parser")
    articles = []
    dl = soup.find("dl")
    if not dl:
        logger.error("No article list found on arXiv page.")
        raise Exception("No article list found on arXiv page.")

    dts = dl.find_all("dt")
    dds = dl.find_all("dd")
    logger.debug("Found %d dt tags and %d dd tags.", len(dts), len(dds))
    for dt, dd in zip(dts, dds):
        id_link = dt.find("a", title="Abstract")
        if not id_link:
            logger.debug("Skipping an article with no abstract link.")
            continue
        article_id = id_link.text.strip()
        pdf_link = dt.find("a", title="Download PDF")
        pdf_url = "https://arxiv.org" + pdf_link["href"] if pdf_link else None

        title_div = dd.find("div", class_="list-title")
        title = (
            title_div.text.replace("Title:", "").strip() if title_div else "No title"
        )

        abstract_div = dd.find("p", class_="mathjax")
        abstract = abstract_div.text.strip() if abstract_div else "No abstract"

        articles.append(
            {
                "id": article_id,
                "title": title,
                "abstract": abstract,
                "pdf_url": pdf_url,
            }
        )
        logger.debug("Parsed article: %s", article_id)

    with open(ARXIV_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f)
    logger.info("Cached %d articles to %s", len(articles), ARXIV_CACHE_FILE)
    return articles


# --- Module: Batched Relevance Filter (Parallelized) ---
def batch_relevance_filter(
    articles,
    user_info,
    batch_size=50,
    llm_url=DEFAULT_LLM_URL,
    model_name=DEFAULT_MODEL_NAME,
):
    """
    Sends articles to the LLM in batches to check their relevance.
    Expects a JSON response mapping article IDs to "yes" or "no".
    This version parallelizes the batched requests.
    """
    relevant_article_ids = set()
    url = llm_url
    logger.info("Starting batched relevance check for %d articles.", len(articles))

    def process_batch(batch):
        local_relevant_ids = set()
        prompt_lines = [f"User info: {user_info}\n"]
        prompt_lines.append(
            "For each of the following articles, determine if it is relevant to the user. Respond in JSON format the keys are the article IDs and the values are 'yes' or 'no', do not add any preamble or any other form of text, your response will be parsed by a json parser immediatelly. remember you have to start your answer with valid json , you cannot add any text, the first char of your answer must be a { , no text."
        )
        for article in batch:
            prompt_lines.append(
                f"Article ID: {article['id']}\nTitle: {article['title']}\nAbstract: {article['abstract']}\n"
            )
        prompt = "\n".join(prompt_lines)
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                logger.error(
                    "LLM batched relevance check failed for batch starting with article '%s' with status code: %d",
                    batch[0]["id"],
                    response.status_code,
                )
                return local_relevant_ids
            data = response.json()
            text_response = data["choices"][0]["message"]["content"].strip()
            try:
                match = re.search(r"\{.*\}", text_response, re.DOTALL)
                if not match:
                    raise ValueError("No valid JSON object found in response")
                json_str = match.group(0)
                logger.debug("Batch response: %s", json_str[:200])
                result = json.loads(json_str)
                for article_id, verdict in result.items():
                    if isinstance(verdict, str) and verdict.lower().strip() == "yes":
                        local_relevant_ids.add(article_id)
            except Exception as e:
                logger.exception("Failed to parse JSON from LLM response: %s", e)
            return local_relevant_ids
        except Exception as e:
            logger.exception("Error during batched relevance check: %s", e)
            return local_relevant_ids

    batches = [
        articles[i : i + batch_size] for i in range(0, len(articles), batch_size)
    ]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_batch, batch) for batch in batches]
        for future in concurrent.futures.as_completed(futures):
            relevant_article_ids.update(future.result())

    logger.info(
        "Batched relevance check complete. %d articles marked as relevant.",
        len(relevant_article_ids),
    )
    return relevant_article_ids


# --- Module: Rerank Articles (Improved JSON extraction) ---
def rerank_articles(
    articles, user_info, llm_url=DEFAULT_LLM_URL, model_name=DEFAULT_MODEL_NAME
):
    """
    Calls the LLM to reorder the articles by importance. Returns the reordered list.
    Expects a JSON response with a 'ranking' key pointing to a list of article IDs, ordered from most relevant to least relevant.
    """
    if not articles:
        return []

    url = llm_url
    logger.info("Starting rerank for %d articles.", len(articles))

    prompt_lines = [
        f"User info: {user_info}\n",
        'Please rank the following articles from most relevant to least relevant. Return your answer as valid JSON in the format: { "ranking": [ "id1", "id2", ... ] }.',
    ]
    for article in articles:
        prompt_lines.append(
            f"Article ID: {article['id']}\nTitle: {article['title']}\nAbstract: {article['abstract']}\n"
        )
    prompt = "\n".join(prompt_lines)
    payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(
                "LLM reranking request failed with status code: %d",
                response.status_code,
            )
            return articles  # fallback: return original order

        data = response.json()
        text_response = data["choices"][0]["message"]["content"].strip()

        match = re.search(r"\{.*\}", text_response, re.DOTALL)
        if not match:
            logger.error("No valid JSON found in rerank response.")
            return articles
        json_str = match.group(0)
        rerank_result = json.loads(json_str)
        ranking_list = rerank_result.get("ranking", [])

        # Create a map for quick lookup
        article_map = {a["id"]: a for a in articles}
        reordered = []
        for art_id in ranking_list:
            if art_id in article_map:
                reordered.append(article_map[art_id])
        # Add any articles not mentioned in the ranking_list, to preserve them at the end
        remaining = [a for a in articles if a["id"] not in ranking_list]
        reordered.extend(remaining)

        return reordered

    except Exception as e:
        logger.exception("Error during rerank: %s", e)
        return articles


# --- Module: Document Converter ---
def fetch_and_convert_article(article):
    """
    Checks for a cached conversion of the article.
    If absent, downloads the PDF, converts it using Docling,
    caches the Markdown text, and returns it.
    """
    safe_id = article["id"].replace(":", "_")
    cache_file = os.path.join(ARTICLES_CACHE_DIR, f"{safe_id}.txt")
    logger.debug("Checking for cached conversion of article '%s'.", article["id"])
    if os.path.exists(cache_file):
        logger.info("Found cached conversion for article '%s'.", article["id"])
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read()

    if not article["pdf_url"]:
        logger.error("No PDF URL for article '%s'. Skipping conversion.", article["id"])
        return ""
    logger.info(
        "Downloading PDF for article '%s' from %s", article["id"], article["pdf_url"]
    )
    response = requests.get(article["pdf_url"])
    if response.status_code != 200:
        logger.error("Failed to download PDF for article '%s'.", article["id"])
        return ""

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(response.content)
        tmp_pdf_path = tmp_pdf.name
    logger.debug("PDF saved temporarily at %s", tmp_pdf_path)

    try:
        logger.info("Converting PDF for article '%s' using Docling.", article["id"])
        conv_result = doc_converter.convert(source=tmp_pdf_path)
        converted_text = conv_result.document.export_to_markdown()
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(converted_text)
        logger.info(
            "Conversion successful for article '%s'. Cached output.", article["id"]
        )
        return converted_text
    except Exception as e:
        logger.exception("Conversion failed for article '%s': %s", article["id"], e)
        return ""
    finally:
        if os.path.exists(tmp_pdf_path):
            os.unlink(tmp_pdf_path)
            logger.debug("Temporary PDF file %s removed.", tmp_pdf_path)


# --- Module: Summarizer (Parallelizable) ---
def generate_article_summary(
    article, content, user_info, llm_url=DEFAULT_LLM_URL, model_name=DEFAULT_MODEL_NAME
):
    """
    Generates a fluid, narrative summary for the article using the LLM.
    The summary starts with a connecting phrase like 'And now,  {article title}'.
    """
    url = llm_url
    prompt = (
        f"User info: {user_info}\n\n"
        f"Please summarize the following article titled '{article['title']}' in a fluid narrative prose style without lists or visual cues. "
        f"Begin the summary with a connecting segment like 'And now, Article: {article['title']}'.\n\n"
        f"Article Content:\n{content}"
    )
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
    }
    logger.info("Generating summary for article '%s'.", article["id"])
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(
                "LLM summarization failed for article '%s'. Status code: %d",
                article["id"],
                response.status_code,
            )
            return ""
        data = response.json()
        summary = data["choices"][0]["message"]["content"].strip()
        logger.debug("Summary for article '%s': %s", article["id"], summary[:100])
        return summary
    except Exception as e:
        logger.exception("Error summarizing article '%s': %s", article["id"], e)
        return ""


# --- Module: TTS Converter ---
def text_to_speech(text, output_mp3):
    """
    Converts the provided text to speech using KPipeline.
    A temporary WAV file is generated and then converted to MP3 using ffmpeg.
    """
    logger.info("Starting text-to-speech conversion.")
    pipeline = KPipeline(lang_code="a")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        temp_wav_path = tmp_wav.name
    logger.debug("Temporary WAV file created at %s", temp_wav_path)

    try:
        generator = pipeline(text, voice="af_bella", speed=1, split_pattern=r"\n+")
        with sf.SoundFile(temp_wav_path, "w", 24000, channels=1) as f:
            for chunk_index, (_, _, audio) in enumerate(generator):
                logger.debug("Writing audio chunk %d to WAV file.", chunk_index)
                f.write(audio)
        logger.info("WAV file generated. Converting to MP3 with ffmpeg.")
        subprocess.run(["ffmpeg", "-y", "-i", temp_wav_path, output_mp3], check=True)
        logger.info("MP3 file created at %s", output_mp3)
    finally:
        if os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
            logger.debug("Temporary WAV file %s removed.", temp_wav_path)


# --- Orchestrator: Process Articles (Parallelizing summarization) ---
def process_articles(
    user_info,
    arxiv_url=DEFAULT_ARXIV_URL,
    llm_url=DEFAULT_LLM_URL,
    model_name=DEFAULT_MODEL_NAME,
    max_articles=5,
    new_only=False,
):
    """
    Executes the full pipeline:
      1. Fetch arXiv articles (cached if available, unless new_only=True).
      2. If new_only, filter out articles that have already been cached as .txt files.
      3. Batch-check relevance via LLM (parallelized).
      4. Re-rank articles by importance using the LLM.
      5. Select the top `max_articles`.
      6. For each selected article, download and convert the PDF to Markdown (sequential).
      7. Generate a narrative summary for each article (parallelized if not cached).
      8. Combine all summaries into a final narrative.
    """
    logger.info("Starting article processing pipeline.")
    # Step 1: fetch articles with potential force_refresh
    articles = fetch_arxiv_list(force_refresh=new_only, arxiv_url=arxiv_url)
    logger.info("Total articles fetched: %d", len(articles))

    # Step 2: if new_only is True, filter out articles older than the most recent cached article
    if new_only:
        cached_articles = [
            f[:-4] for f in os.listdir(ARTICLES_CACHE_DIR) if f.endswith(".txt")
        ]
        if cached_articles:

            def parse_id(id_str):
                if id_str.lower().startswith("ar"):
                    id_str = id_str[6:]
                parts = id_str.split(".")
                return (int(parts[0][:2]), int(parts[0][2:]), int(parts[1]))

            most_recent = max(cached_articles, key=parse_id)
            articles = [
                article
                for article in articles
                if parse_id(article["id"]) > parse_id(most_recent)
            ]
            logger.info(
                "After filtering by most recent article id %s, %d articles remain.",
                most_recent,
                len(articles),
            )
        else:
            logger.info(
                "No cached articles found, proceeding with all fetched articles."
            )

    # Step 3: batch relevance check (parallelized)
    relevant_ids = batch_relevance_filter(
        articles, user_info, llm_url=llm_url, model_name=model_name
    )
    relevant_articles = [
        article for article in articles if article["id"] in relevant_ids
    ]
    logger.info(
        "Found %d relevant articles out of %d.", len(relevant_articles), len(articles)
    )

    # Step 4: rerank
    reranked_articles = rerank_articles(
        relevant_articles, user_info, llm_url=llm_url, model_name=model_name
    )

    # Step 5: select top max_articles
    final_candidates = reranked_articles[:max_articles]

    # Step 6: convert PDFs sequentially
    articles_with_content = []
    for article in final_candidates:
        content = fetch_and_convert_article(article)
        if content:
            articles_with_content.append((article, content))
        else:
            logger.warning("No content obtained for article '%s'.", article["id"])

    # Step 7: generate summaries in parallel
    summaries = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_article = {
            executor.submit(
                generate_article_summary,
                article,
                content,
                user_info,
                llm_url,
                model_name,
            ): article
            for article, content in articles_with_content
        }
        for future in concurrent.futures.as_completed(future_to_article):
            article = future_to_article[future]
            try:
                summary = future.result()
                if summary:
                    summaries.append(summary)
                else:
                    logger.warning(
                        "No summary generated for article '%s'.", article["id"]
                    )
            except Exception as e:
                logger.exception(
                    "Error generating summary for article '%s': %s", article["id"], e
                )

    # Step 8: combine summaries
    final_summary = "\n\n".join(summaries) + " "
    final_summary += f"\n\nThanks for listening to the report. Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} by vibe.py"

    logger.info(
        "Final summary generated with length %d characters.", len(final_summary)
    )
    return final_summary


# --- Flask Application ---
app = Flask(__name__)


@app.route("/process", methods=["POST"])
def process_endpoint():
    """
    Expects JSON with a 'user_info' field.
    Optionally accepts 'max_articles' (default 5) and 'new_only' (boolean).
    Runs the complete pipeline and returns the final MP3 file.
    """
    data = request.get_json()
    user_info = data.get("user_info", "")
    if not user_info:
        logger.error("user_info not provided in request.")
        return jsonify({"error": "user_info not provided"}), 400

    max_articles = data.get("max_articles", 5)
    new_only = data.get("new_only", False)

    logger.info(
        "Processing request with user_info: %s, max_articles: %s, new_only: %s",
        user_info,
        max_articles,
        new_only,
    )
    final_summary = process_articles(
        user_info,
        arxiv_url=DEFAULT_ARXIV_URL,
        llm_url=DEFAULT_LLM_URL,
        model_name=DEFAULT_MODEL_NAME,
        max_articles=max_articles,
        new_only=new_only,
    )
    if not final_summary.strip():
        logger.error("No summaries generated.")
        return jsonify({"error": "No summaries generated."}), 500

    output_mp3 = os.path.join(CACHE_DIR, "final_output.mp3")
    try:
        text_to_speech(final_summary, output_mp3)
    except Exception as e:
        logger.exception("TTS conversion failed: %s", e)
        return jsonify({"error": f"TTS conversion failed: {e}"}), 500

    logger.info("Process complete. Returning MP3 file.")
    return send_file(output_mp3, as_attachment=True)


# --- Main ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="vibe: Article Summarization & TTS Pipeline"
    )
    parser.add_argument("--serve", action="store_true", help="Run as a Flask server.")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run the pipeline once, generate a summary MP3, then exit.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="",
        help="User info (interests, context) for LLM filtering & summaries.",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=5,
        help="Maximum articles to process in the pipeline.",
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="If set, only process articles newer than cached.",
    )
    parser.add_argument(
        "--arxiv-url",
        type=str,
        default=DEFAULT_ARXIV_URL,
        help="URL for fetching arXiv articles.",
    )
    parser.add_argument(
        "--llm-url", type=str, default=DEFAULT_LLM_URL, help="URL of the LLM endpoint."
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help="Name of model to pass to the LLM endpoint.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="final_output.mp3",
        help="Output path for the generated MP3 file.",
    )

    args = parser.parse_args()

    if args.serve:
        logger.info("Starting Flask application in verbose mode.")
        app.run(debug=True)
    elif args.generate:
        # Run the pipeline directly and produce an MP3 file
        logger.info("Running pipeline in CLI mode.")
        user_info = args.prompt
        final_summary = process_articles(
            user_info=user_info,
            arxiv_url=args.arxiv_url,
            llm_url=args.llm_url,
            model_name=args.model_name,
            max_articles=args.max_articles,
            new_only=args.new_only,
        )
        if not final_summary.strip():
            logger.error("No summaries generated.")
            exit(1)

        output_mp3 = args.output
        try:
            text_to_speech(final_summary, output_mp3)
            logger.info(f"Generated MP3 at: {output_mp3}")
        except Exception as e:
            logger.exception("TTS conversion failed: %s", e)
            exit(1)
    else:
        # Default to Flask server if neither flag is set
        logger.info("No --serve or --generate specified; running Flask by default.")
        app.run(debug=True)
