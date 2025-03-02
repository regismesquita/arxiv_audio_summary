import requests
import logging
from .config import DEFAULT_LLM_URL, DEFAULT_MODEL_NAME

logger = logging.getLogger(__name__)

def generate_article_summary(article, content, user_info, llm_url=None, model_name=None):
    """
    Generates a fluid, narrative summary for the article using the LLM.
    The summary starts with a connecting phrase.
    """
    if llm_url is None or model_name is None:
        llm_url = DEFAULT_LLM_URL
        model_name = DEFAULT_MODEL_NAME

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
        response = requests.post(llm_url, json=payload)
        if response.status_code != 200:
            logger.error("LLM summarization failed for article '%s'. Status code: %d", article["id"], response.status_code)
            return ""
        data = response.json()
        summary = data["choices"][0]["message"]["content"].strip()
        logger.debug("Summary for article '%s': %s", article["id"], summary[:100])
        return summary
    except Exception as e:
        logger.exception("Error summarizing article '%s': %s", article["id"], e)
        return ""