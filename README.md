# vibe: Article Summarization & TTS Pipeline

vibe is a Python-based pipeline that automatically fetches the latest Computer Science research articles from arXiv, filters them for relevance using a language model (LLM), converts article PDFs to Markdown with Docling, generates narrative summaries, and synthesizes the summaries into an MP3 audio file using a text-to-speech (TTS) system. This tool is ideal for users who prefer listening to curated research summaries on the go or integrating the process into a larger system via an API.

## Features

- **Fetch Articles:** Retrieves the latest Computer Science articles from arXiv.
- **Cache Mechanism:** Caches article metadata and converted content to speed up subsequent requests.
- **Relevance Filtering:** Uses an LLM to filter articles based on user-provided interests.
- **PDF Conversion:** Converts PDF articles to Markdown format using Docling.
- **Summarization:** Generates a fluid, narrative-style summary for each relevant article with the help of an LLM.
- **Text-to-Speech:** Converts the final narrative summary into an MP3 file using KPipeline.
- **Flask API:** Exposes the functionality via a RESTful endpoint for dynamic requests.
- **CLI and Server Modes:** Run the pipeline as a one-off CLI command or as a continuously running Flask server.

## Why Use vibe?

- **Stay Updated:** Automatically curate and summarize the latest research articles so you can keep up with advancements in your field.
- **Hands-Free Listening:** Enjoy audio summaries during your commute or while multitasking.
- **Automated Workflow:** Seamlessly integrate multiple processing steps—from fetching and filtering to summarization and TTS.
- **Flexible Deployment:** Use the CLI mode for quick summaries or deploy the Flask API for integration with other systems.

## Installation

1. **Prerequisites:**
   Ensure you have Python 3.x installed on your system.

2. **Clone the Repository:**
   Clone this repository to your local machine.

3. **Install Dependencies:**
   Navigate to the project directory and install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

### CLI Mode

Run the pipeline once to generate an MP3 summary file. For example:
```
python vibe.py --generate --prompt "I live in a mid-sized European city, working in the tech industry on AI-driven automation solutions. I prefer content focused on deep learning and reinforcement learning applications, and I want to filter out less relevant topics. Only include articles that are rated 9 or 10 on a relevance scale from 0 to 10." --max-articles 10 --output summary_cli.mp3
```
This command fetches the latest articles from arXiv, filters and ranks them based on your specified interests, generates narrative summaries, and converts the final summary into an MP3 file named `summary_cli.mp3`.

### Server Mode

Alternatively, you can run vibe as a Flask server:
```
python vibe.py --serve
```
Once the server is running, you can process requests by sending a POST request to the `/process` endpoint. For example:
```
curl -X POST http://127.0.0.1:5000/process \
     -H "Content-Type: application/json" \
     -d '{"user_info": "Your interests here", "max_articles": 5, "new_only": false}'
```
The server processes the articles, generates an MP3 summary, and returns the file as a downloadable response.

## Environment Variables

The following environment variables can be set to customize the behavior of vibe:

- `ARXIV_URL`: The URL used to fetch the latest arXiv articles. Defaults to `https://arxiv.org/list/cs/new`.
- `LLM_URL`: The URL for the language model endpoint. Defaults to `http://127.0.0.1:4000/v1/chat/completions` (this is a litellm instance).
- `MODEL_NAME`: The model name to be used by the LLM. Defaults to `mistral-small-latest`.

Note that using the `mistral-small` model through their cloud service typically costs a few cents per run and completes the summarization process in around 4 minutes. It is also possible to run vibe with local LLMs (such as qwen 2.5 14b or mistral-small), although these local runs may take up to an hour.

## Project Structure

- **vibe.py:** Main application file containing modules for:
  - Fetching and caching arXiv articles.
  - Filtering articles for relevance.
  - Converting PDFs to Markdown using Docling.
  - Summarizing articles via an LLM.
  - Converting text summaries to speech (MP3) using KPipeline.
  - Exposing a Flask API for processing requests.
- **requirements.txt:** Contains the list of Python packages required by the project.
- **CACHE_DIR:** Directory created at runtime for caching articles and processed files.

## Dependencies

The project relies on several key libraries:
- Flask
- requests
- beautifulsoup4
- soundfile
- docling
- kokoro

## Contributing

Contributions are welcome! Feel free to fork this repository and submit pull requests with improvements or bug fixes.

## License

This project is licensed under the MIT License.

## Acknowledgments

Thanks to the developers of [Docling](https://github.com/docling) and [Kokoro](https://github.com/kokoro) as well as the maintainers of BeautifulSoup and Flask for providing great tools that made this project possible.