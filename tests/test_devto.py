import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

from devto_engine import (
    clean_text,
    html_to_markdown,
    sanitize_devto_tags,
    build_devto_payload,
    load_state,
    save_state
)

class TestDevtoSyndicator(unittest.TestCase):

    def test_clean_text(self):
        raw = "<h2>AI Governance &amp; Digital Rights</h2>"
        self.assertEqual(clean_text(raw), "AI Governance & Digital Rights")

    def test_html_to_markdown(self):
        html_input = (
            "<h2>Heading Title</h2>"
            "<p>This is a paragraph with <a href=\"https://aviperera.com\">link</a> and <strong>bold</strong> text.</p>"
            "<blockquote>Important quote</blockquote>"
        )
        md = html_to_markdown(html_input)
        self.assertIn("## Heading Title", md)
        self.assertIn("[link](https://aviperera.com)", md)
        self.assertIn("**bold**", md)
        self.assertIn("> Important quote", md)

    def test_sanitize_devto_tags(self):
        categories = ["AI Ethics", "Legal & Policy!", "Autonomous Systems", "Machine Learning", "Extra"]
        tags = sanitize_devto_tags(categories)
        self.assertLessEqual(len(tags), 4)
        for t in tags:
            self.assertTrue(t.isalnum())
            self.assertTrue(t.islower())
            self.assertLessEqual(len(t), 20)

    def test_build_devto_payload(self):
        post = {
            "title": "Corporate Liability for Autonomous Systems",
            "link": "https://aviperera.com/corporate-liability-autonomous-systems/",
            "content_html": "<p>Forensic examination of product liability.</p>",
            "description": "Short summary",
            "categories": ["AI", "Governance"],
            "image_url": "https://aviperera.com/sample.jpg"
        }
        payload = build_devto_payload(post, published=True)
        art = payload["article"]

        self.assertEqual(art["title"], "Corporate Liability for Autonomous Systems")
        self.assertEqual(art["canonical_url"], "https://aviperera.com/corporate-liability-autonomous-systems/")
        self.assertTrue(art["published"])
        self.assertIn("aviperera.com", art["body_markdown"])
        self.assertIn("main_image", art)
        self.assertEqual(art["main_image"], "https://aviperera.com/sample.jpg")

    def test_load_and_save_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_state_file = os.path.join(tmpdir, "state", "devto_history.json")
            with patch("devto_engine.STATE_FILE", test_state_file):
                state = load_state()
                self.assertEqual(state["syndicated"], {})

                state["syndicated"]["post-101"] = {
                    "title": "Sample Article",
                    "canonical_url": "https://aviperera.com/sample-article",
                    "devto_id": "999"
                }
                save_state(state)

                reloaded = load_state()
                self.assertIn("post-101", reloaded["syndicated"])
                self.assertEqual(reloaded["syndicated"]["post-101"]["devto_id"], "999")

if __name__ == "__main__":
    unittest.main()
