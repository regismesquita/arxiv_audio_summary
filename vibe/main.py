import argparse
import logging
from vibe.orchestrator import process_articles
from vibe.tts import text_to_speech
from vibe.config import DEFAULT_ARXIV_URL

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
    parser.add_argument("--output", type=str, default="final_output.mp3", help="Output path for the generated MP3 file.")

    # New: LLM Level
    parser.add_argument("--llm-level", type=str, default="medium", choices=["low","medium","high"],
                        help="Desired LLM quality level: low, medium, or high. Defaults to medium.")

    args = parser.parse_args()

    if args.serve:
        from vibe.server import app
        logger.info("Starting Flask server.")
        app.run(host='0.0.0.0', port='14200', debug=True)
    elif args.generate:
        logger.info("Running pipeline in CLI mode.")
        user_info = args.prompt
        final_summary = process_articles(
            user_info,
            arxiv_url=args.arxiv_url,
            max_articles=args.max_articles,
            new_only=args.new_only,
            llm_level=args.llm_level
        )
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
        app.run(host='0.0.0.0', port='14200', debug=True)

if __name__ == "__main__":
    main()
