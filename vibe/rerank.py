import json
import re
import requests
import logging

logger = logging.getLogger(__name__)

def rerank_articles(articles, user_info, llm_url=None, model_name=None):
    """
    Calls the LLM to reorder the articles by importance. Returns the reordered list.
    Expects a JSON response with a 'ranking' key pointing to a list of article IDs.
    """
    if not articles:
        return []

    if llm_url is None or model_name is None:
        from .config import DEFAULT_LLM_URL, DEFAULT_MODEL_NAME
        llm_url = llm_url or DEFAULT_LLM_URL
        model_name = model_name or DEFAULT_MODEL_NAME

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
        response = requests.post(llm_url, json=payload)
        if response.status_code != 200:
            logger.error("LLM reranking request failed with status code: %d", response.status_code)
            return articles
        data = response.json()
        text_response = data["choices"][0]["message"]["content"].strip()
        match = re.search(r"\{.*\}", text_response, re.DOTALL)
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