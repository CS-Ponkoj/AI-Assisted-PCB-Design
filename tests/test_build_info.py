import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.build_info import app_version, commit_id, get_build_info, normalize_commit


class BuildInfoTests(unittest.TestCase):
    def test_version_and_commit_metadata_are_short_and_non_sensitive(self):
        self.assertEqual(app_version(), "5.1.0")
        self.assertEqual(normalize_commit("ABCDEF0123456789"), "abcdef0")
        self.assertEqual(normalize_commit("not-a-commit-or-secret"), "unknown")

        with patch.dict("os.environ", {"APP_COMMIT_SHA": "0123456789abcdef"}, clear=False):
            self.assertEqual(commit_id(), "0123456")
            info = get_build_info()

        self.assertEqual(info["App version"], "5.1.0")
        self.assertEqual(info["Commit"], "0123456")
        self.assertIn("Python", info)
        self.assertIn("Streamlit", info)
        self.assertIn("Gemini model", info)

    def test_deployment_details_render_on_initial_app_page(self):
        with patch("src.gemini_assistant.get_gemini_api_key", return_value=""), patch(
            "src.review_copilot.get_gemini_api_key",
            return_value="",
        ), patch("src.build_info.commit_id", return_value="0123456"):
            app_test = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60)
            app_test.run()

        self.assertFalse(app_test.exception)
        self.assertIn("Deployment details", [item.label for item in app_test.expander])
        self.assertTrue(any(item.value.startswith("App 5.1.0 · build ") for item in app_test.caption))


if __name__ == "__main__":
    unittest.main()
