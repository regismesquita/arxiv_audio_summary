import os
import logging
import concurrent.futures
from datetime import datetime

from .config import ARTICLES_CACHE_DIR
from .fetcher import fetch_arxiv_list
from .filter import batch_relevance_filter
from .rerank import rerank_articles
from .converter import fetch_and_convert_article
from .summarizer import generate_article_summary
from .tts import text_to_speech

logger = logging.getLogger(__name__)

def process_articles(user_info, arxiv_url=None, llm_url=None, model_name=None, max_articles=5, new_only=False, trace_callback=None):
    """
    Executes the full pipeline:
      1. Fetch arXiv articles.
      2. Optionally filter out articles older than cached ones if new_only is True.
      3. Batch-check relevance via LLM.
      4. Rerank articles.
      5. Select top max_articles.
      6. Convert PDFs to Markdown.
      7. Generate narrative summaries.
      8. Combine summaries into a final narrative.
    """
    if trace_callback:
        trace_callback("Starting pipeline: fetching arXiv articles...")
    articles = fetch_arxiv_list(force_refresh=new_only, arxiv_url=arxiv_url)
    if trace_callback:
        trace_callback(f"Fetched {len(articles)} articles from arXiv.")

    if new_only:
        if trace_callback:
            trace_callback("Filtering articles for new content based on cache...")
        cached_articles = [f[:-4] for f in os.listdir(ARTICLES_CACHE_DIR) if f.endswith(".txt")]
        if cached_articles:
            def parse_id(id_str):
                if id_str.lower().startswith("ar"):
                    id_str = id_str[6:]
                parts = id_str.split(".")
                return (int(parts[0][:2]), int(parts[0][2:]), int(parts[1]))
            most_recent = max(cached_articles, key=parse_id)
            articles = [article for article in articles if parse_id(article["id"]) > parse_id(most_recent)]
            if trace_callback:
                trace_callback(f"After filtering by most recent article id {most_recent}, {len(articles)} articles remain.")
        else:
            if trace_callback:
                trace_callback("No cached articles found; processing all fetched articles.")

    if trace_callback:
        trace_callback("Performing relevance filtering via LLM...")
    relevant_ids = batch_relevance_filter(articles, user_info, llm_url=llm_url, model_name=model_name)
    relevant_articles = [article for article in articles if article["id"] in relevant_ids]
    if trace_callback:
        trace_callback(f"Identified {len(relevant_articles)} relevant articles out of {len(articles)}.")

    if trace_callback:
        trace_callback("Reranking articles based on relevance...")
    reranked_articles = rerank_articles(relevant_articles, user_info, llm_url=llm_url, model_name=model_name)
    final_candidates = reranked_articles[:max_articles]

    if trace_callback:
        trace_callback("Converting article PDFs to Markdown...")
    articles_with_content = []
    for article in final_candidates:
        content = fetch_and_convert_article(article)
        if content:
            articles_with_content.append((article, content))
            if trace_callback:
                trace_callback(f"Converted article {article['id']} to Markdown.")
        else:
            logger.warning("No content obtained for article '%s'.", article["id"])
            if trace_callback:
                trace_callback(f"Failed to convert article {article['id']}.")

    if trace_callback:
        trace_callback("Generating narrative summaries for articles...")
    summaries = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_article = {
            executor.submit(generate_article_summary, article, content, user_info, llm_url, model_name): article
            for article, content in articles_with_content
        }
        for future in concurrent.futures.as_completed(future_to_article):
            article = future_to_article[future]
            try:
                summary = future.result()
                if summary:
                    summaries.append(summary)
                    if trace_callback:
                        trace_callback(f"Generated summary for article {article['id']}.")
                else:
                    logger.warning("No summary generated for article '%s'.", article["id"])
                    if trace_callback:
                        trace_callback(f"Summary generation failed for article {article['id']}.")
            except Exception as e:
                logger.exception("Error generating summary for article '%s': %s", article["id"], e)
                if trace_callback:
                    trace_callback(f"Error generating summary for article {article['id']}.")

    final_summary = "\n\n".join(summaries)
    final_summary += f"\n\nThanks for listening to the report. Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} by vibe."
    if trace_callback:
        trace_callback("Final summary generated. Starting TTS conversion.")
    logger.info("Final summary generated with length %d characters.", len(final_summary))
    return final_summary
