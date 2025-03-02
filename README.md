# vibe: Your Personal AI Research Summarizer 🎧

**vibe** is a smart assistant that fetches the latest Computer Science research articles from arXiv, identifies the most relevant ones based on your interests, summarizes them into engaging narratives, and even reads them aloud by generating an MP3 audio summary. Perfect for staying informed effortlessly!

---

## 🎯 What Can vibe Do for You?

- Automatically fetch the newest CS research from arXiv.
- Filter and rank articles tailored to your specific interests.
- Summarize articles into a smooth, narrative-friendly format.
- Generate an MP3 audio summary to listen on-the-go.
- Provide real-time progress updates while generating your summaries.

---

## 🚀 Quick Start Guide

### ✅ Step 1: Installation

Make sure you have Python (3.x) installed, then run:

```bash
pip install -r requirements.txt
```

### ✅ Step 2: Clone vibe to Your Machine

```bash
git clone <repository_url>
cd vibe
```

### 🛠 Running vibe

You can use vibe in two ways: via a command-line interface (CLI) or through a friendly web interface with real-time updates.

#### 1️⃣ CLI Mode

To quickly generate an audio summary directly from your terminal:

```bash
python vibe/main.py --generate --prompt "Your interests here" --max-articles 5 --output summary.mp3
```

Your audio summary will be saved as `summary.mp3`. Just play and enjoy!

#### 2️⃣ Server Mode (Recommended 🎉)

We’ve built a simple, intuitive web landing page that lets you interact easily with vibe:

First, launch the Flask server by running:

```bash
python vibe/main.py --serve
```

Then open your web browser and go to:

```
http://127.0.0.1:5000
```

#### ✨ How It Works:

- Enter your interests directly on the landing page.
- Click “Submit” and relax while vibe fetches and summarizes the best articles for you.
- Watch live status updates appear on-screen, letting you know exactly what’s happening behind the scenes.
- Once complete, an audio summary (`summary.mp3`) will automatically download. It’s that easy!

---

## 🧪 Running Tests

Ensure vibe stays reliable with the built-in test suite. Just run:

```bash
make test
```

Or manually:

```bash
python -m unittest discover -s tests
```

---

## ⚙️ Makefile Commands

We’ve made common tasks simpler:

- `make test` – Runs unit tests.
- `make run` – Runs vibe in CLI mode (you can customize this command inside the Makefile).
- `make serve` – Starts the Flask server with the web interface.
- `make clean` – Cleans temporary files (cache, temporary directories).

---

## 🌎 Environment Variables

Customize vibe with these optional environment variables:

- `ARXIV_URL` – URL for fetching articles from arXiv.
- `LLM_URL` – URL of your preferred language model endpoint.
- `MODEL_NAME` – Name of the language model to use.

---

## 📜 License

vibe is open source under the MIT License. Use it, modify it, enjoy it!

---

✨ Enjoy exploring the latest research effortlessly with vibe! ✨