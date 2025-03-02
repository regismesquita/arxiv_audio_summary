# vibe: Article Summarization & TTS Pipeline

vibe is a Python-based pipeline that automatically fetches the latest Computer Science research articles from arXiv, filters them for relevance using a language model (LLM), converts article PDFs to Markdown with Docling, generates narrative summaries, and synthesizes the summaries into an MP3 audio file using a text-to-speech (TTS) system.

This repository has been refactored into a modular structure for improved maintainability.

## Project Structure

- **vibe/** - Main package containing all modules:
  - `config.py` - Configuration, constants, and cache setup.
  - `fetcher.py` - Module to fetch articles from arXiv.
  - `filter.py` - Module for relevance filtering using an LLM.
  - `rerank.py` - Module to rerank articles.
  - `converter.py` - Module to convert PDFs to Markdown.
  - `summarizer.py` - Module to generate article summaries.
  - `tts.py` - Module for text-to-speech conversion.
  - `orchestrator.py` - Orchestrates the complete pipeline.
  - `server.py` - Flask server exposing a REST API.
  - `main.py` - CLI entry point.
- **tests/** - Contains unit tests.
- **requirements.txt** - Python package requirements.
- **Makefile** - Makefile to run common tasks.

## Installation

1. **Prerequisites:**
   - Python 3.x
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

2. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd <repository_directory>

Running the Application

CLI Mode

To generate a summary MP3 using the CLI:

python vibe/main.py --generate --prompt "Your interests and context here" --max-articles 5 --output summary.mp3

Server Mode

To run the Flask server:

python vibe/main.py --serve

Then, you can make a POST request to http://127.0.0.1:5000/process with a JSON payload:

curl -X POST http://127.0.0.1:5000/process \
     -H "Content-Type: application/json" \
     -d '{"user_info": "Your interests here", "max_articles": 5, "new_only": false}'

Running Tests

The project includes basic tests to verify that modules are working as expected. To run the tests, execute:

make test

or

python -m unittest discover -s tests

Makefile Commands
    •	make test - Run the unit tests.
    •	make run - Run the application in CLI mode (you can modify the command inside the Makefile).
    •	make serve - Run the Flask server.
    •	make clean - Clean up temporary files (e.g., remove the cache directory).

Environment Variables

The following environment variables can be set to customize the behavior:
    •	ARXIV_URL
    •	LLM_URL
    •	MODEL_NAME

License

This project is licensed under the MIT License.