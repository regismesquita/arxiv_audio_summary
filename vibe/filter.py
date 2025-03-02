import json
import re
import requests
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

def batch_relevance_filter(articles, user_info, batch_size=50, llm_url=None, model_name=None):
    """
    Sends articles to the LLM in batches to check their relevance.
    Expects a JSON response mapping article IDs to "yes" or "no".
    This version parallelizes the batched requests.
    """
    if llm_url is None or model_name is None:
        from .config import DEFAULT_LLM_URL, DEFAULT_MODEL_NAME
        llm_url = llm_url or DEFAULT_LLM_URL
        model_name = model_name or DEFAULT_MODEL_NAME

    relevant_article_ids = set()
    logger.info("Starting batched relevance check for %d articles.", len(articles))

    def process_batch(batch):
        local_relevant_ids = set()
        prompt_lines = [f"User info: {user_info}\n"]
        prompt_lines.append(
            "For each of the following articles, determine if it is relevant to the user. Respond in JSON format with keys as the article IDs and values as 'yes' or 'no'. Do not add any extra text; the response must start with a '{'."
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
            response = requests.post(llm_url, json=payload)
            if response.status_code != 200:
                logger.error("LLM batched relevance check failed for batch starting with article '%s' with status code: %d", batch[0]["id"], response.status_code)
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

    batches = [articles[i: i + batch_size] for i in range(0, len(articles), batch_size)]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_batch, batch) for batch in batches]
        for future in concurrent.futures.as_completed(futures):
            relevant_article_ids.update(future.result())

    logger.info("Batched relevance check complete. %d articles marked as relevant.", len(relevant_article_ids))
    return relevant_article_ids