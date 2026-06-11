import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


class FakeResponse:
    def __init__(self, url, content, content_type):
        self.url = url
        self.content = content
        self.text = content.decode("utf-8")
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        return None


class SourceCacheTests(unittest.TestCase):
    def test_fetch_url_reuses_cached_file_without_second_request(self):
        import fetch_paper

        with tempfile.TemporaryDirectory() as tmp:
            calls = {"count": 0}
            original_dir = fetch_paper.DOWNLOADED_DIR
            fetch_paper.DOWNLOADED_DIR = Path(tmp)

            def fake_get(url, **kwargs):
                calls["count"] += 1
                return FakeResponse(url, b"<html>paper</html>", "text/html")

            try:
                first = fetch_paper.fetch_url("https://example.com/paper", get_fn=fake_get)
                second = fetch_paper.fetch_url("https://example.com/paper", get_fn=fake_get)
            finally:
                fetch_paper.DOWNLOADED_DIR = original_dir

            self.assertEqual(first, second)
            self.assertEqual(calls["count"], 1)
            self.assertTrue(Path(first).with_suffix(Path(first).suffix + ".fetch.json").exists())

    def test_extract_text_reuses_cached_output_for_unchanged_source(self):
        import extract_text

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "paper.html"
            source.write_text("<html><body><p>Paper text</p></body></html>", encoding="utf-8")
            calls = {"count": 0}

            def fake_extract(path):
                calls["count"] += 1
                return "Paper text"

            first = extract_text.extract_to_text_file(str(source), html_extractor=fake_extract)
            second = extract_text.extract_to_text_file(str(source), html_extractor=fake_extract)

            self.assertEqual(first, second)
            self.assertEqual(calls["count"], 1)
            self.assertTrue(Path(first).with_suffix(Path(first).suffix + ".extract.json").exists())

    def test_normalize_text_reuses_cached_output_for_unchanged_text(self):
        import normalize_text

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paper.txt"
            path.write_text("A\n\n\nB", encoding="utf-8")

            first = normalize_text.normalize_file(str(path))
            mtime = Path(first).stat().st_mtime_ns
            second = normalize_text.normalize_file(str(path))

            self.assertEqual(first, second)
            self.assertEqual(Path(second).read_text(encoding="utf-8"), "A\n\nB")
            self.assertEqual(Path(second).stat().st_mtime_ns, mtime)
            self.assertTrue(Path(second).with_suffix(Path(second).suffix + ".normalize.json").exists())


if __name__ == "__main__":
    unittest.main()
