import logging
from .llm import chat_llm

logger = logging.getLogger(__name__)

def generate_article_summary(article, content, user_info, llm_level="medium"):
    """
    Generates a fluid, narrative summary for the article using the LLM.
    The summary starts with a connecting phrase.
    """
    prompt = (
        f"User info: {user_info}\n\n"
        f"Please summarize the following article titled '{article['title']}' in a fluid narrative prose style without lists or visual cues. "
        f"Begin the summary with a connecting segment like 'And now, Article: {article['title']}'.\n\n"
        f"Article Content:\n{content}"
    )

    logger.info("Generating summary for article '%s'.", article["id"])
    try:
        response_text = chat_llm(prompt, level=llm_level)
        return response_text
    except Exception as e:
        logger.exception("Error summarizing article '%s': %s", article["id"], e)
        return ""