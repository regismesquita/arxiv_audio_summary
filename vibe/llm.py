import os
import logging
import litellm
import tomli

logger = logging.getLogger(__name__)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "llm_config.toml")

try:
    with open(CONFIG_PATH, "rb") as f:
        _CONFIG = tomli.load(f)
except FileNotFoundError:
    logger.warning("LLM config file llm_config.toml not found. Using default settings.")
    exit(-1)


def chat_llm(prompt: str, level: str = "medium") -> str:
    """
    Sends 'prompt' to the LLM defined by the 'level' block in llm_config.toml.
    Returns the LLM's text output.
    """
    llm_settings = _CONFIG["llms"].get(level, {})
    api_key = llm_settings.get("api_key", os.environ.get("MISTRAL_API_KEY"))
    api_base = llm_settings.get("api_base", "https://api.mistral.ai")
    model = llm_settings.get("model", "mistral/mistral-small-latest")

    try:
        # Using the litellm library to call the chat endpoint
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_base=api_base,
            api_key=api_key,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.exception("Error calling LLM: %s", e)
        return ""
