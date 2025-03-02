from flask import Flask, send_file, request, jsonify, render_template
import logging
from .orchestrator import process_articles
from .config import CACHE_DIR

logger = logging.getLogger(__name__)
app = Flask(__name__)

@app.route("/process", methods=["POST"])
def process_endpoint():
    data = request.get_json()
    user_info = data.get("user_info", "")
    if not user_info:
        logger.error("user_info not provided in request.")
        return jsonify({"error": "user_info not provided"}), 400

    max_articles = data.get("max_articles", 5)
    new_only = data.get("new_only", False)

    logger.info("Processing request with user_info: %s, max_articles: %s, new_only: %s", user_info, max_articles, new_only)
    final_summary = process_articles(user_info, max_articles=max_articles, new_only=new_only)
    if not final_summary.strip():
        logger.error("No summaries generated.")
        return jsonify({"error": "No summaries generated."}), 500

    output_mp3 = f"{CACHE_DIR}/final_output.mp3"
    try:
        from .tts import text_to_speech
        text_to_speech(final_summary, output_mp3)
    except Exception as e:
        logger.exception("TTS conversion failed: %s", e)
        return jsonify({"error": f"TTS conversion failed: {e}"}), 500

    logger.info("Process complete. Returning MP3 file.")
    return send_file(output_mp3, as_attachment=True)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)