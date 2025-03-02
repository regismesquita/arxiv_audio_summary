import argparse
import logging
from vibe.orchestrator import process_articles
from vibe.tts import text_to_speech
from vibe.config import DEFAULT_ARXIV_URL, DEFAULT_LLM_URL, DEFAULT_MODEL_NAME

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="vibe: Article Summarization & TTS Pipeline")
    parser.add_argument("--serve", action="store_true", help="Run as a Flask server.")
    parser.add_argument("--generate", action="store_true", help="Run the pipeline once and generate a summary MP3, then exit.")
    parser.add_argument("--prompt", type=str, default="", help="User info for LLM filtering & summaries.")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum articles to process in the pipeline.")
    parser.add_argument("--new-only", action="store_true", help="Only process articles newer than cached.")
    parser.add_argument("--arxiv-url", type=str, default=DEFAULT_ARXIV_URL, help="URL for fetching arXiv articles.")
    parser.add_argument("--llm-url", type=str, default=DEFAULT_LLM_URL, help="URL of the LLM endpoint.")
    parser.add_argument("--model-name", type=str, default=DEFAULT_MODEL_NAME, help="Name of model to pass to the LLM endpoint.")
    parser.add_argument("--output", type=str, default="final_output.mp3", help="Output path for the generated MP3 file.")
    
    args = parser.parse_args()

    if args.serve:
        from vibe.server import app
        logger.info("Starting Flask server.")
        app.run(debug=True)
    elif args.generate:
        logger.info("Running pipeline in CLI mode.")
        user_info = args.prompt
        final_summary = process_articles(user_info, arxiv_url=args.arxiv_url, llm_url=args.llm_url, model_name=args.model_name, max_articles=args.max_articles, new_only=args.new_only)
        if not final_summary.strip():
            logger.error("No summaries generated.")
            exit(1)
        try:
            text_to_speech(final_summary, args.output)
            logger.info(f"Generated MP3 at: {args.output}")
        except Exception as e:
            logger.exception("TTS conversion failed: %s", e)
            exit(1)
    else:
        logger.info("No mode specified; defaulting to Flask server.")
        from vibe.server import app
        app.run(debug=True)

if __name__ == "__main__":
    main()