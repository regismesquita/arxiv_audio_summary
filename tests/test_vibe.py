import unittest
from unittest.mock import patch, MagicMock

# Import modules from the vibe package
from vibe.fetcher import fetch_arxiv_list
from vibe.filter import batch_relevance_filter
from vibe.rerank import rerank_articles
from vibe.converter import fetch_and_convert_article
from vibe.summarizer import generate_article_summary
from vibe.orchestrator import process_articles

class TestVibeModules(unittest.TestCase):

    @patch("vibe.fetcher.requests.get")
    def test_fetch_arxiv_list(self, mock_get):
        # Setup a fake response for arXiv HTML
        fake_html = """
        <html>
          <body>
            <dl>
              <dt><a title="Abstract">arXiv:1234.5678</a> <a title="Download PDF" href="/pdf/1234.5678.pdf"></a></dt>
              <dd>
                <div class="list-title">Title: Test Article</div>
                <p class="mathjax">This is a test abstract.</p>
              </dd>
            </dl>
          </body>
        </html>
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = fake_html
        articles = fetch_arxiv_list(force_refresh=True, arxiv_url="http://fakeurl")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["id"], "arXiv:1234.5678")

    @patch("vibe.filter.requests.post")
    def test_batch_relevance_filter(self, mock_post):
        # Simulate LLM response
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"choices": [{"message": {"content": '{"arXiv:1234.5678": "yes"}'}}]}
        mock_post.return_value = fake_response

        articles = [{"id": "arXiv:1234.5678", "title": "Test", "abstract": "Test abstract"}]
        relevant_ids = batch_relevance_filter(articles, "dummy user")
        self.assertIn("arXiv:1234.5678", relevant_ids)

    @patch("vibe.rerank.requests.post")
    def test_rerank_articles(self, mock_post):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"choices": [{"message": {"content": '{"ranking": ["arXiv:1234.5678"]}'}}]}
        mock_post.return_value = fake_response

        articles = [{"id": "arXiv:1234.5678", "title": "Test", "abstract": "Test abstract"}]
        ranked = rerank_articles(articles, "dummy user")
        self.assertEqual(ranked[0]["id"], "arXiv:1234.5678")

    @patch("vibe.converter.requests.get")
    def test_fetch_and_convert_article(self, mock_get):
        # This test will simulate a failure to download a PDF
        article = {"id": "arXiv:1234.5678", "pdf_url": "http://fakepdf", "title": "Test", "abstract": "Test abstract"}
        mock_get.return_value.status_code = 404
        content = fetch_and_convert_article(article)
        self.assertEqual(content, "")

    @patch("vibe.summarizer.requests.post")
    def test_generate_article_summary(self, mock_post):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"choices": [{"message": {"content": "Summary text"}}]}
        mock_post.return_value = fake_response
        summary = generate_article_summary({"id": "arXiv:1234.5678", "title": "Test"}, "content", "dummy user")
        self.assertEqual(summary, "Summary text")

    @patch("vibe.orchestrator.fetch_arxiv_list")
    @patch("vibe.orchestrator.batch_relevance_filter")
    @patch("vibe.orchestrator.rerank_articles")
    @patch("vibe.orchestrator.fetch_and_convert_article")
    @patch("vibe.orchestrator.generate_article_summary")
    def test_process_articles(self, mock_summary, mock_convert, mock_rerank, mock_filter, mock_fetch):
        # Setup mocks for orchestrator pipeline
        mock_fetch.return_value = [{
            "id": "arXiv:1234.5678",
            "title": "Test Article",
            "abstract": "Test abstract",
            "pdf_url": "http://fakepdf"
        }]
        mock_filter.return_value = {"arXiv:1234.5678"}
        mock_rerank.return_value = [{
            "id": "arXiv:1234.5678",
            "title": "Test Article",
            "abstract": "Test abstract",
            "pdf_url": "http://fakepdf"
        }]
        mock_convert.return_value = "Converted content"
        mock_summary.return_value = "Final summary"

        summary = process_articles("dummy user", max_articles=1)
        self.assertIn("Final summary", summary)

if __name__ == "__main__":
    unittest.main()