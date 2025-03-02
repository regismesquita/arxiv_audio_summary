from flask import Flask, send_file, request, jsonify, render_template
import logging
from vibe.orchestrator import process_articles
from vibe.config import CACHE_DIR

from flask_socketio import SocketIO, emit

logger = logging.getLogger(__name__)
app = Flask(__name__, template_folder="../templates")
socketio = SocketIO(app)

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
    # Define trace_callback to emit trace messages via WebSockets
    def trace_callback(message):
        socketio.emit("trace", {"message": message})
    final_summary = process_articles(user_info, arxiv_url=None, llm_url=None, model_name=None, max_articles=max_articles, new_only=new_only, trace_callback=trace_callback)
    if not final_summary.strip():
        logger.error("No summaries generated.")
        return jsonify({"error": "No summaries generated."}), 500

    import uuid, os
    mp3_filename = f"final_{uuid.uuid4().hex}.mp3"
    output_mp3 = os.path.join(CACHE_DIR, mp3_filename)

    try:
        from vibe.tts import text_to_speech
        text_to_speech(final_summary, output_mp3)
        trace_callback("Text-to-Speech conversion complete. MP3 file generated.")
    except Exception as e:
        logger.exception("TTS conversion failed: %s", e)
        return jsonify({"error": f"TTS conversion failed: {e}"}), 500

    logger.info("Process complete. Returning MP3 file.")
    return send_file(output_mp3, as_attachment=True)

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    emit("trace", {"message": "Connected to server. Ready to process your request."})

if __name__ == "__main__":
    socketio.run(app, debug=True)