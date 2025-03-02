import os
import json
import requests
from bs4 import BeautifulSoup
import logging
from .config import ARXIV_CACHE_FILE

logger = logging.getLogger(__name__)

def fetch_arxiv_list(force_refresh=False, arxiv_url=None):
    """
    Fetches the latest CS articles from arXiv. If a cache exists, reads from it
    unless force_refresh is True. Otherwise, parses the arXiv page, extracts
    article metadata, and caches it.
    """
    if arxiv_url is None:
        from .config import DEFAULT_ARXIV_URL
        arxiv_url = DEFAULT_ARXIV_URL

    logger.debug("Checking for cached arXIV list at %s", ARXIV_CACHE_FILE)
    if not force_refresh and os.path.exists(ARXIV_CACHE_FILE):
        logger.info("Cache found for arXiv list. Loading from cache.")
        with open(ARXIV_CACHE_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)
        logger.debug("Loaded %d articles from cache.", len(articles))
        return articles

    logger.info("Fetching arXiv page from %s", arxiv_url)
    response = requests.get(arxiv_url)
    if response.status_code != 200:
        logger.error("Failed to fetch arXiv page. Status code: %d", response.status_code)
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
        title = title_div.text.replace("Title:", "").strip() if title_div else "No title"

        abstract_div = dd.find("p", class_="mathjax")
        abstract = abstract_div.text.strip() if abstract_div else "No abstract"

        articles.append({
            "id": article_id,
            "title": title,
            "abstract": abstract,
            "pdf_url": pdf_url,
        })
        logger.debug("Parsed article: %s", article_id)

    with open(ARXIV_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f)
    logger.info("Cached %d articles to %s", len(articles), ARXIV_CACHE_FILE)
    return articles