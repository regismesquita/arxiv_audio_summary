import json
import re
import logging

from .llm import chat_llm

logger = logging.getLogger(__name__)

def rerank_articles(articles, user_info, llm_level="medium"):
    """
    Calls the LLM to reorder the articles by importance. Returns the reordered list.
    Expects a JSON response with a 'ranking' key pointing to a list of article IDs.
    """
    if not articles:
        return []

    logger.info("Starting rerank for %d articles.", len(articles))
    prompt_lines = [
        f"User info: {user_info}\n",
        ('Please rank the following articles from most relevant to least relevant. '
         'Return your answer as valid JSON in the format: { "ranking": [ "id1", "id2", ... ] }.')
    ]
    for article in articles:
        prompt_lines.append(
            f"Article ID: {article['id']}\nTitle: {article['title']}\nAbstract: {article['abstract']}\n"
        )
    prompt = "\n".join(prompt_lines)

    try:
        response_text = chat_llm(prompt, level=llm_level)
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not match:
            logger.error("No valid JSON found in rerank response.")
            return articles
        json_str = match.group(0)
        rerank_result = json.loads(json_str)
        ranking_list = rerank_result.get("ranking", [])
        article_map = {a["id"]: a for a in articles}
        reordered = [article_map[art_id] for art_id in ranking_list if art_id in article_map]
        remaining = [a for a in articles if a["id"] not in ranking_list]
        reordered.extend(remaining)
        return reordered
    except Exception as e:
        logger.exception("Error during rerank: %s", e)
        return articles