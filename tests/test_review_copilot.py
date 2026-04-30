import copy
import json
import unittest
from unittest.mock import patch

import app
from src.review_copilot import (
    build_review_context,
    deterministic_review_answer,
    format_sources,
    run_gemini_review_copilot,
    run_review_copilot,
)


def generated_package(requirement: str):
    package = app.generate_design_package(requirement)
    package["readiness_review"] = app.generate_design_readiness_review(package)
    return package


class ReviewCopilotTests(unittest.TestCase):
    def test_review_context_is_built_from_generated_package_without_mutating_it(self):
        package = generated_package("temperature humidity light")
        before = json.dumps(package, sort_keys=True)

        context = build_review_context(package)
        context["bom"][0]["Item"] = "Changed in context only"

        self.assertEqual(json.dumps(package, sort_keys=True), before)
        self.assertEqual(context["requirement"]["selected_components"], ["AHT20", "BH1750"])
        self.assertEqual(context["readiness"]["status"], "Needs Review")
        self.assertEqual(package["bom"][0]["Item"], "USB-C receptacle")

    def test_local_copilot_risk_answer_uses_readiness_and_fabrication_sources(self):
        package = generated_package("temperature with GPS and camera")
        context = build_review_context(package)

        answer = deterministic_review_answer("Find design risks", context)

        self.assertEqual(answer["mode"], "local")
        self.assertIn("Blocked", answer["answer"])
        self.assertIn("Unsupported request", answer["answer"])
        self.assertIn("Readiness Review", answer["sources"])
        self.assertIn("Fabrication Checklist", answer["sources"])

    def test_local_copilot_change_request_is_scoped_and_does_not_mutate_package(self):
        package = generated_package("temperature humidity light")
        before = copy.deepcopy(package)

        answer = run_review_copilot("What happens if I remove the light sensor?", package)

        self.assertIn("will not mutate", answer["answer"])
        self.assertIn("BH1750", answer["answer"])
        self.assertEqual(package, before)

    def test_gemini_review_copilot_reports_unavailable_when_key_is_missing(self):
        package = generated_package("temperature humidity light")
        context = build_review_context(package)

        with patch("src.review_copilot.get_gemini_api_key", return_value=""):
            answer = run_gemini_review_copilot("Explain the power budget", context)

        self.assertEqual(answer["mode"], "gemini_unavailable")
        self.assertIn("Scope Guardrail", answer["sources"])
        self.assertIn("Gemini Review Copilot is unavailable", answer["answer"])
        self.assertTrue(any("Gemini API key" in note for note in answer["guardrail_notes"]))

    def test_gemini_review_copilot_validates_sources_and_keeps_contract(self):
        package = generated_package("temperature humidity")
        context = build_review_context(package)

        with patch(
            "src.review_copilot.call_gemini_review_generate",
            return_value={
                "answer": "AHT20 is selected for the generated temperature and humidity sensing scope.",
                "sources": ["Parsed Requirement", "Imaginary Datasheet"],
                "confidence": "high",
                "guardrail_notes": ["Answered from context."],
            },
        ):
            answer = run_gemini_review_copilot("Why was AHT20 selected?", context, api_key="fake-key")

        self.assertEqual(answer["mode"], "gemini")
        self.assertIn("Parsed Requirement", answer["sources"])
        self.assertNotIn("Imaginary Datasheet", answer["sources"])
        self.assertEqual(answer["confidence"], "high")

    def test_app_copilot_uses_local_review_when_gemini_is_busy(self):
        package = generated_package("temperature humidity light")

        with patch("src.review_copilot.get_gemini_api_key", return_value="fake-key"), patch(
            "src.review_copilot.call_gemini_review_generate",
            side_effect=RuntimeError("Gemini busy"),
        ):
            answer = app.run_review_copilot("Find design risks", package)

        self.assertEqual(answer["mode"], "local_review")
        self.assertIn("Readiness status", answer["answer"])
        self.assertIn("Readiness Review", answer["sources"])

    def test_format_sources_is_user_readable(self):
        self.assertEqual(format_sources(["BOM", "Netlist"]), "Based on: BOM, Netlist")

    def test_suggested_questions_include_core_review_paths_and_selected_component(self):
        package = generated_package("temperature humidity light")
        context = build_review_context(package)

        questions = app.review_copilot_question_bank(context)

        self.assertIn("Top risks", questions)
        self.assertIn("Bring-up plan", questions)
        self.assertIn("I2C and key nets", questions)
        self.assertIn("Remove BH1750?", questions)
        self.assertEqual(app.review_copilot_question_text("Top risks"), "What are the top design risks?")
        self.assertEqual(app.review_copilot_question_text("Remove BH1750?"), "What happens if I remove BH1750?")

    def test_power_budget_answer_separates_individual_load_from_total(self):
        package = generated_package("temperature humidity light")
        context = build_review_context(package)

        answer = deterministic_review_answer("Explain the power budget", context)

        self.assertIn("largest individual load is ESP32-WROOM-32", answer["answer"])
        self.assertIn("total estimated 3.3 V load", answer["answer"])
        self.assertNotIn("largest individual load is 3.3 V regulator requirement", answer["answer"])

    def test_copilot_ui_renders_compact_suggestions_and_scrollable_chat(self):
        from streamlit.testing.v1 import AppTest

        with patch("src.gemini_assistant.get_gemini_api_key", return_value=""), patch(
            "src.review_copilot.get_gemini_api_key",
            return_value="",
        ):
            at = AppTest.from_file("app.py", default_timeout=60)
            at.run()
            at.text_area[0].set_value("USB-C board with WiFi Bluetooth temperature humidity light")
            at.button[0].click().run()

            button_labels = [button.label for button in at.button]
            self.assertIn("Top risks", button_labels)
            self.assertIn("Power budget", button_labels)
            self.assertIn("Ask Copilot", button_labels)
            self.assertNotIn("Use Gemini for richer review answers", [toggle.label for toggle in at.toggle])
            self.assertEqual(at.text_input[0].label, "Ask local review question")

            at.button[button_labels.index("Top risks")].click().run()

        self.assertFalse(at.exception)
        self.assertTrue(any("**You**" in item.value for item in at.info))
        self.assertTrue(any("What are the top design risks?" in item.value for item in at.info))
        self.assertTrue(any("**Copilot**" in item.value for item in at.success))
        self.assertTrue(any("Readiness status" in item.value for item in at.success))
        self.assertFalse(any("Gemini Review Copilot is unavailable" in item.value for item in at.warning))
        self.assertFalse(any("copilot-chatbox" in item.value for item in at.markdown))
        self.assertFalse(any("<style>" in item.value for item in at.markdown))

    def test_copilot_ui_orders_copilot_before_supporting_diagrams_and_clears_chat(self):
        from streamlit.testing.v1 import AppTest

        with patch("src.gemini_assistant.get_gemini_api_key", return_value=""), patch(
            "src.review_copilot.get_gemini_api_key",
            return_value="",
        ):
            at = AppTest.from_file("app.py", default_timeout=60)
            at.run()
            at.text_area[0].set_value("USB-C board with WiFi Bluetooth temperature humidity light")
            at.button[0].click().run()

            expander_labels = [expander.label for expander in at.expander]
            self.assertIn("System architecture and schematic connectivity", expander_labels)
            self.assertNotIn("More suggested questions", expander_labels)

            button_labels = [button.label for button in at.button]
            at.button[button_labels.index("Top risks")].click().run()
            button_labels = [button.label for button in at.button]
            at.button[button_labels.index("Clear Chat")].click().run()

        self.assertFalse(at.exception)
        self.assertTrue(any("Gemini is unavailable. Local Review Mode is active" in item.value for item in at.info))
        self.assertFalse(any(item.value.startswith("**Copilot**") for item in at.success))

    def test_copilot_ui_switches_to_local_questions_when_gemini_runtime_fails(self):
        from streamlit.testing.v1 import AppTest

        with patch("src.gemini_assistant.get_gemini_api_key", return_value="fake-key"), patch(
            "src.review_copilot.get_gemini_api_key",
            return_value="fake-key",
        ), patch(
            "src.review_copilot.call_gemini_review_generate",
            side_effect=RuntimeError("Gemini busy"),
        ):
            at = AppTest.from_file("app.py", default_timeout=60)
            at.run()
            at.text_area[0].set_value("USB-C board with WiFi Bluetooth temperature humidity light")
            at.button[0].click().run()
            button_labels = [button.label for button in at.button]
            at.button[button_labels.index("Top risks")].click().run()

        self.assertFalse(at.exception)
        self.assertEqual(at.text_input[0].label, "Ask local review question")
        self.assertTrue(any("Local-safe suggested questions" in item.value for item in at.markdown))
        self.assertTrue(any("Readiness status" in item.value for item in at.success))
        self.assertTrue(any("Mode: local_review" in item.value or "Mode: local review" in item.value for item in at.caption))


if __name__ == "__main__":
    unittest.main()
