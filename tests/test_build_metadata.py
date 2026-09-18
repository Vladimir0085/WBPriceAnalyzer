from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from wb_app import __version__
from wb_app.config import APP_VERSION
from scripts.generate_version_info import (
    render_version_info,
    windows_version_tuple,
    write_version_info,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BuildMetadataTests(unittest.TestCase):
    def test_application_uses_package_version(self) -> None:
        self.assertEqual(APP_VERSION, __version__)

    def test_windows_version_tuple_accepts_release_suffix(self) -> None:
        self.assertEqual(windows_version_tuple("1.2.3"), (1, 2, 3, 0))
        self.assertEqual(windows_version_tuple("2.4.6.8-beta+build.9"), (2, 4, 6, 8))

    def test_windows_version_tuple_rejects_invalid_values(self) -> None:
        for invalid in ("", "1.two.3", "1.2.3.4.5", "1.70000"):
            with self.subTest(version=invalid), self.assertRaises(ValueError):
                windows_version_tuple(invalid)

    def test_version_resource_contains_product_metadata(self) -> None:
        rendered = render_version_info("3.2.1")
        self.assertIn("filevers=(3, 2, 1, 0)", rendered)
        self.assertIn("StringStruct('FileVersion', '3.2.1')", rendered)
        self.assertIn("StringStruct('ProductName', 'WB Price Analyzer')", rendered)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "windows_version_info.txt"
            self.assertEqual(write_version_info(destination, "3.2.1"), destination.resolve())
            self.assertEqual(destination.read_text(encoding="utf-8"), rendered)

    def test_pyproject_reads_version_from_package(self) -> None:
        metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertIn("version", metadata["project"]["dynamic"])
        self.assertEqual(
            metadata["tool"]["setuptools"]["dynamic"]["version"]["attr"],
            "wb_app.__version__",
        )
        self.assertEqual(
            metadata["project"]["scripts"]["wbpriceanalyzer"],
            "wb_app.report_totals:run_app",
        )

    def test_windows_build_files_reference_portable_application(self) -> None:
        spec_path = PROJECT_ROOT / "WBPriceAnalyzer.spec"
        compile(spec_path.read_text(encoding="utf-8"), str(spec_path), "exec")
        spec_text = spec_path.read_text(encoding="utf-8")
        self.assertIn('name="WBPriceAnalyzer"', spec_text)
        self.assertIn('"wb_app/resources"', spec_text)
        self.assertIn('resources / "cost_template.xlsx"', spec_text)

        workflow = (PROJECT_ROOT / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("WBPriceAnalyzer-Windows-x64", workflow)
        self.assertIn("smoke_test_windows.ps1", workflow)
        smoke_test = (PROJECT_ROOT / "scripts/smoke_test_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("SingleInstanceWindowProbe", smoke_test)
        self.assertIn("Второй экземпляр не завершился", smoke_test)

    def test_windows_package_contains_the_versioned_pdf_instruction(self) -> None:
        guide = PROJECT_ROOT / "docs" / f"WBPriceAnalyzer_Instruction_v{__version__}.pdf"
        self.assertTrue(guide.is_file())
        self.assertGreater(guide.stat().st_size, 50_000)
        self.assertEqual(guide.read_bytes()[:5], b"%PDF-")

        workflow = (PROJECT_ROOT / ".github/workflows/windows-build.yml").read_text(
            encoding="utf-8"
        )
        batch = (PROJECT_ROOT / "build_windows.bat").read_text(encoding="utf-8")
        generator = (PROJECT_ROOT / "scripts" / "generate_user_manual_pdf.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("WBPriceAnalyzer_Instruction_v$version.pdf", workflow)
        self.assertIn("WBPriceAnalyzer_Instruction_v%APP_VERSION%.pdf", batch)
        self.assertIn(f'VERSION = "{__version__}"', generator)


    def test_about_dialog_references_project_repository(self) -> None:
        ui_text = (PROJECT_ROOT / "wb_app/ui.py").read_text(encoding="utf-8")
        repository_url = "https://github.com/Vladimir0085/WBPriceAnalyzer"
        self.assertIn(repository_url, ui_text)
        self.assertNotIn("github.com/otdelvsego-spec/WBPriceAnalyzer", ui_text)


if __name__ == "__main__":
    unittest.main()
