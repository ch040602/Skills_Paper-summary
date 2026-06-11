import os
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


class AssetCacheTests(unittest.TestCase):
    def test_reuses_cached_assets_for_unchanged_pdf(self):
        from asset_cache import load_or_extract_pdf_assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "paper.pdf"
            asset_dir = root / "assets"
            pdf_path.write_bytes(b"%PDF-1.4 unchanged")
            calls = {"figures": 0, "tables": 0}

            def extract_figures(pdf, out_dir):
                calls["figures"] += 1
                Path(out_dir, "figure_01_p01.png").write_bytes(b"png")
                return [{"number": 1, "filename": "figure_01_p01.png", "page": 1}]

            def extract_tables(pdf):
                calls["tables"] += 1
                return [{"number": "1", "caption": "Result", "page": 1, "markdown": "| A | B |\n| --- | --- |\n| 1 | 2 |"}]

            first_figures, first_tables = load_or_extract_pdf_assets(
                str(pdf_path), str(asset_dir), extract_figures, extract_tables
            )
            second_figures, second_tables = load_or_extract_pdf_assets(
                str(pdf_path), str(asset_dir), extract_figures, extract_tables
            )

            self.assertEqual(first_figures, second_figures)
            self.assertEqual(first_tables, second_tables)
            self.assertEqual(calls, {"figures": 1, "tables": 1})

    def test_invalidates_cache_when_pdf_changes(self):
        from asset_cache import load_or_extract_pdf_assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "paper.pdf"
            asset_dir = root / "assets"
            pdf_path.write_bytes(b"%PDF-1.4 first")
            calls = {"figures": 0, "tables": 0}

            def extract_figures(pdf, out_dir):
                calls["figures"] += 1
                filename = f"figure_{calls['figures']:02d}_p01.png"
                Path(out_dir, filename).write_bytes(b"png")
                return [{"number": calls["figures"], "filename": filename, "page": 1}]

            def extract_tables(pdf):
                calls["tables"] += 1
                return [{"number": str(calls["tables"]), "caption": "Result", "page": 1, "markdown": "| A | B |"}]

            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)
            time.sleep(0.02)
            pdf_path.write_bytes(b"%PDF-1.4 changed")
            os.utime(pdf_path, None)
            figures, tables = load_or_extract_pdf_assets(
                str(pdf_path), str(asset_dir), extract_figures, extract_tables
            )

            self.assertEqual(calls, {"figures": 2, "tables": 2})
            self.assertEqual(figures[0]["number"], 2)
            self.assertEqual(tables[0]["number"], "2")

    def test_invalidates_cache_when_cached_figure_file_is_missing(self):
        from asset_cache import load_or_extract_pdf_assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "paper.pdf"
            asset_dir = root / "assets"
            pdf_path.write_bytes(b"%PDF-1.4 unchanged")
            calls = {"figures": 0, "tables": 0}

            def extract_figures(pdf, out_dir):
                calls["figures"] += 1
                Path(out_dir, "figure_01_p01.png").write_bytes(b"png")
                return [{"number": 1, "filename": "figure_01_p01.png", "page": 1}]

            def extract_tables(pdf):
                calls["tables"] += 1
                return []

            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)
            (asset_dir / "figure_01_p01.png").unlink()
            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)

            self.assertEqual(calls, {"figures": 2, "tables": 2})

    def test_invalidates_cache_when_pdf_bytes_change_but_size_and_mtime_are_preserved(self):
        from asset_cache import load_or_extract_pdf_assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "paper.pdf"
            asset_dir = root / "assets"
            pdf_path.write_bytes(b"%PDF-1.4 version-a")
            original_stat = pdf_path.stat()
            calls = {"figures": 0, "tables": 0}

            def extract_figures(pdf, out_dir):
                calls["figures"] += 1
                filename = f"figure_{calls['figures']:02d}_p01.png"
                Path(out_dir, filename).write_bytes(b"png")
                return [{"number": calls["figures"], "filename": filename, "page": 1}]

            def extract_tables(pdf):
                calls["tables"] += 1
                return []

            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)
            pdf_path.write_bytes(b"%PDF-1.4 version-b")
            os.utime(pdf_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)

            self.assertEqual(calls, {"figures": 2, "tables": 2})

    def test_invalidates_cache_when_manifest_has_no_tables_field(self):
        from asset_cache import CACHE_FILENAME, load_or_extract_pdf_assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "paper.pdf"
            asset_dir = root / "assets"
            pdf_path.write_bytes(b"%PDF-1.4 unchanged")
            calls = {"figures": 0, "tables": 0}

            def extract_figures(pdf, out_dir):
                calls["figures"] += 1
                Path(out_dir, "figure_01_p01.png").write_bytes(b"png")
                return [{"number": 1, "filename": "figure_01_p01.png", "page": 1}]

            def extract_tables(pdf):
                calls["tables"] += 1
                return [{"number": "1", "caption": "Result", "page": 1, "markdown": "| A |"}]

            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)
            cache_path = asset_dir / CACHE_FILENAME
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            payload.pop("tables")
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
            load_or_extract_pdf_assets(str(pdf_path), str(asset_dir), extract_figures, extract_tables)

            self.assertEqual(calls, {"figures": 2, "tables": 2})


if __name__ == "__main__":
    unittest.main()
