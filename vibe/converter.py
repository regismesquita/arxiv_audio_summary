import os
import json
import tempfile
import requests
import logging
import subprocess
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

from .config import ARTICLES_CACHE_DIR

logger = logging.getLogger(__name__)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options.use_gpu = False
pipeline_options.generate_picture_images = False
pdf_options = PdfFormatOption(pipeline_options=pipeline_options)
doc_converter = DocumentConverter(format_options={InputFormat.PDF: pdf_options})
doc_converter = DocumentConverter()

def fetch_and_convert_article(article):
    """
    Checks for a cached conversion of the article.
    If absent, downloads the PDF, converts it using Docling,
    caches the Markdown text, and returns it.
    """
    safe_id = article["id"].replace(":", "_")
    cache_file = os.path.join(ARTICLES_CACHE_DIR, f"{safe_id}.txt")
    logger.debug("Checking for cached conversion of article '%s'.", article["id"])
    if os.path.exists(cache_file):
        logger.info("Found cached conversion for article '%s'.", article["id"])
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read()

    if not article["pdf_url"]:
        logger.error("No PDF URL for article '%s'. Skipping conversion.", article["id"])
        return ""
    logger.info("Downloading PDF for article '%s' from %s", article["id"], article["pdf_url"])
    response = requests.get(article["pdf_url"])
    if response.status_code != 200:
        logger.error("Failed to download PDF for article '%s'.", article["id"])
        return ""

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(response.content)
        tmp_pdf_path = tmp_pdf.name
    logger.debug("PDF saved temporarily at %s", tmp_pdf_path)

    try:
        logger.info("Converting PDF for article '%s' using Docling.", article["id"])
        conv_result = doc_converter.convert(source=tmp_pdf_path)
        converted_text = conv_result.document.export_to_markdown()
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(converted_text)
        logger.info("Conversion successful for article '%s'. Cached output.", article["id"])
        return converted_text
    except SystemExit as se:
        logger.exception("Docling conversion exited with error code %s for article '%s'. Skipping conversion.", se.code, article["id"])
        return ""
    except Exception as e:
        logger.exception("Conversion failed for article '%s': %s", article["id"], e)
        return ""
    finally:
        if os.path.exists(tmp_pdf_path):
            os.unlink(tmp_pdf_path)
            logger.debug("Temporary PDF file %s removed.", tmp_pdf_path)
