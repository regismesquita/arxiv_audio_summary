import os
import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
    logger.debug("Created cache directory: %s", CACHE_DIR)

ARXIV_CACHE_FILE = os.path.join(CACHE_DIR, "arxiv_list.json")
ARTICLES_CACHE_DIR = os.path.join(CACHE_DIR, "articles")
if not os.path.exists(ARTICLES_CACHE_DIR):
    os.makedirs(ARTICLES_CACHE_DIR)
    logger.debug("Created articles cache directory: %s", ARTICLES_CACHE_DIR)

DEFAULT_ARXIV_URL = os.environ.get("ARXIV_URL", "https://arxiv.org/list/cs/new")
DEFAULT_LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:4000/v1/chat/completions")
DEFAULT_MODEL_NAME = os.environ.get("MODEL_NAME", "mistral-small-latest")