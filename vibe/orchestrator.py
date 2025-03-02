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

def process_articles(user_info, arxiv_url=None, llm_url=None, model_name=None, max_articles=5, new_only=False):
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
    articles = fetch_arxiv_list(force_refresh=new_only, arxiv_url=arxiv_url)
    logger.info("Total articles fetched: %d", len(articles))

    if new_only:
        cached_articles = [f[:-4] for f in os.listdir(ARTICLES_CACHE_DIR) if f.endswith(".txt")]
        if cached_articles:
            def parse_id(id_str):
                if id_str.lower().startswith("ar"):
                    id_str = id_str[6:]
                parts = id_str.split(".")
                return (int(parts[0][:2]), int(parts[0][2:]), int(parts[1]))
            most_recent = max(cached_articles, key=parse_id)
            articles = [article for article in articles if parse_id(article["id"]) > parse_id(most_recent)]
            logger.info("After filtering by most recent article id %s, %d articles remain.", most_recent, len(articles))
        else:
            logger.info("No cached articles found, proceeding with all fetched articles.")

    relevant_ids = batch_relevance_filter(articles, user_info, llm_url=llm_url, model_name=model_name)
    relevant_articles = [article for article in articles if article["id"] in relevant_ids]
    logger.info("Found %d relevant articles out of %d.", len(relevant_articles), len(articles))

    reranked_articles = rerank_articles(relevant_articles, user_info, llm_url=llm_url, model_name=model_name)
    final_candidates = reranked_articles[:max_articles]

    articles_with_content = []
    for article in final_candidates:
        content = fetch_and_convert_article(article)
        if content:
            articles_with_content.append((article, content))
        else:
            logger.warning("No content obtained for article '%s'.", article["id"])

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
                else:
                    logger.warning("No summary generated for article '%s'.", article["id"])
            except Exception as e:
                logger.exception("Error generating summary for article '%s': %s", article["id"], e)

    final_summary = "\n\n".join(summaries)
    final_summary += f"\n\nThanks for listening to the report. Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} by vibe."
    logger.info("Final summary generated with length %d characters.", len(final_summary))
    return final_summary