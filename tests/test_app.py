import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
from src.base_assistant import validate_ai_extraction
from src.gemini_assistant import (
    check_gemini_status,
    get_gemini_api_key,
    get_gemini_model_candidates,
    run_gemini_requirement_assistant,
)
from src.ollama_assistant import (
    build_ollama_headers,
    check_ollama_status,
    get_ollama_provider_label,
    read_int_env,
    run_ollama_requirement_assistant,
)


class PcbGeneratorTests(unittest.TestCase):
    def test_temperature_humidity_light_selection(self):
        package = app.generate_design_package(
            "USB-C board with WiFi Bluetooth temperature humidity light"
        )

        self.assertEqual(
            package["parsed"]["requested_sensing"],
            ["temperature", "humidity", "light"],
        )
        self.assertEqual(package["parsed"]["selected_components"], ["AHT20", "BH1750"])
        self.assertTrue(any(row["Item"] == "AHT20" for row in package["bom"]))
        self.assertTrue(any(row["Item"] == "BH1750" for row in package["bom"]))

    def test_stable_refs_match_visual_footprints(self):
        light_package = app.generate_design_package("light sensing")
        pressure_package = app.generate_design_package("pressure sensing")

        self.assertEqual(light_package["sensor_refs"], {"BH1750": "U4"})
        self.assertEqual(pressure_package["sensor_refs"], {"BMP280": "U6"})

        light_svg = app.generate_pcb_visual_svg(
            light_package["parsed"]["selected_components"],
            light_package["sensor_refs"],
        )
        self.assertIn("U3 AHT20", light_svg)
        self.assertIn("U4 BH1750", light_svg)
        self.assertNotIn("U3 BH1750", light_svg)

    def test_unsupported_requests_are_reported(self):
        parsed = app.parse_requirements("temperature with GPS and camera")

        self.assertEqual(parsed["selected_components"], ["AHT20"])
        self.assertIn("gps", parsed["unsupported_requirements"])
        self.assertIn("camera", parsed["unsupported_requirements"])

    def test_sensor_schema_validation_rejects_bad_sensor(self):
        with tempfile.TemporaryDirectory() as root:
            sensor_dir = Path(root) / "BAD"
            sensor_dir.mkdir()
            (sensor_dir / "sensor.json").write_text(
                json.dumps({"component": "BAD"}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                app.load_sensor_definitions(root)

    def test_new_sensor_folder_can_be_loaded_without_app_changes(self):
        with tempfile.TemporaryDirectory() as root:
            sensor_dir = Path(root) / "SOIL123"
            sensor_dir.mkdir()
            (sensor_dir / "sensor.json").write_text(
                json.dumps(
                    {
                        "component": "SOIL123",
                        "display_name": "SOIL123",
                        "order": 50,
                        "interface": "I2C",
                        "functions": "Soil moisture",
                        "categories": [
                            {
                                "name": "soil_moisture",
                                "function": "Soil moisture sensing",
                                "keywords": ["soil moisture", "soil"],
                            }
                        ],
                        "linked_categories": [],
                        "i2c_address": "0x44",
                        "supply": "3.3 V",
                        "current_ma": 0.5,
                        "footprint": "Generic I2C sensor footprint",
                        "pins": {
                            "VCC": "3V3",
                            "GND": "GND",
                            "SDA": "I2C_SDA",
                            "SCL": "I2C_SCL",
                        },
                        "placement": "Place near sensing connector.",
                        "routing": "Route as a short I2C stub.",
                    }
                ),
                encoding="utf-8",
            )

            loaded = app.load_sensor_definitions(root)
            supported = app.build_supported_sensors(loaded)
            keywords = app.build_sensor_keywords(loaded)

            self.assertEqual(supported["soil_moisture"]["component"], "SOIL123")
            self.assertEqual(keywords["soil moisture"], "soil_moisture")

    def test_disabled_template_sensor_is_not_loaded(self):
        self.assertNotIn("NEW_SENSOR_PART", app.SENSOR_LIBRARY)
        rows = app.collect_sensor_validation()
        template_rows = [row for row in rows if row["Sensor"] == "NEW_SENSOR_PART"]
        self.assertEqual(template_rows[0]["Status"], "Disabled")

    def test_optional_extra_pin_is_added_to_netlist(self):
        with tempfile.TemporaryDirectory() as root:
            sensor_dir = Path(root) / "IRQ123"
            sensor_dir.mkdir()
            (sensor_dir / "sensor.json").write_text(
                json.dumps(
                    {
                        "component": "IRQ123",
                        "display_name": "IRQ123",
                        "order": 50,
                        "interface": "I2C",
                        "functions": "Interrupt sensor",
                        "categories": [
                            {
                                "name": "interrupt_test",
                                "function": "Interrupt test sensing",
                                "keywords": ["interrupt test"],
                            }
                        ],
                        "linked_categories": [],
                        "i2c_address": "0x45",
                        "supply": "3.3 V",
                        "current_ma": 0.5,
                        "footprint": "Generic I2C sensor footprint",
                        "pins": {
                            "VCC": "3V3",
                            "GND": "GND",
                            "SDA": "I2C_SDA",
                            "SCL": "I2C_SCL",
                            "INT": "GPIO_INT_OPTIONAL",
                        },
                        "placement": "Place near sensing connector.",
                        "routing": "Route as a short I2C stub.",
                    }
                ),
                encoding="utf-8",
            )

            loaded = app.load_sensor_definitions(root)
            refs = app.build_sensor_reference_map(loaded, app.BOARD_TEMPLATE)
            original_library = app.SENSOR_LIBRARY
            try:
                app.SENSOR_LIBRARY = loaded
                rows = app.generate_netlist_table(["IRQ123"], refs)
            finally:
                app.SENSOR_LIBRARY = original_library

            self.assertTrue(any(row["Net"] == "GPIO_INT_OPTIONAL" for row in rows))

    def test_pcb_visual_height_is_dynamic(self):
        self.assertGreaterEqual(app.calculate_pcb_visual_height(), 640)
        svg = app.generate_pcb_visual_svg(["AHT20"], {"AHT20": "U3"})
        self.assertIn("Clear top-view PCB layout visual", svg)
        self.assertIn("INSTALL", svg)
        self.assertIn("DNP OPTION", svg)

    def test_export_package_contains_designer_handoff_files(self):
        package = app.generate_design_package("temperature humidity light")
        exports = app.generate_export_package(package)

        self.assertIn("Ref,Item,Value / Part,Qty", exports["bom_csv"])
        self.assertIn("AHT20", exports["bom_csv"])
        self.assertIn("BH1750", exports["bom_csv"])
        self.assertIn("Ref,Pin,Net", exports["pin_map_csv"])
        self.assertIn("Net,Connected pins,Type,Voltage", exports["netlist_csv"])
        self.assertIn("# PCB Designer Handoff Report", exports["report_markdown"])
        self.assertIn("## Bill of Materials", exports["report_markdown"])
        self.assertEqual(json.loads(exports["report_json"])["parsed"]["selected_components"], ["AHT20", "BH1750"])

    def test_local_assistant_infers_natural_language_without_api(self):
        parsed, meta = app.generate_ai_requirements("room comfort brightness and air freshness, no camera")

        self.assertTrue(meta["used_ai"])
        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750", "SGP30"])
        self.assertEqual(
            parsed["requested_sensing"],
            ["temperature", "humidity", "light", "air_quality"],
        )
        self.assertIn("camera", parsed["unsupported_requirements"])
        self.assertEqual(parsed["ai_assistant"]["mode"], "local")

    def test_llm_assistant_falls_back_when_ollama_unavailable(self):
        parsed, meta = run_ollama_requirement_assistant(
            "room comfort brightness",
            app.SENSOR_LIBRARY,
            app.SUPPORTED_SENSORS,
            app.SENSOR_KEYWORDS,
            app.REQUIREMENT_GROUPS,
            app.REQUIREMENT_CONFIG,
            base_url="http://127.0.0.1:1",
        )

        self.assertEqual(meta["mode"], "local_fallback")
        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750"])
        self.assertEqual(parsed["ai_assistant"]["mode"], "local_fallback")
        self.assertEqual(meta["provider"], "Local Ollama")

    def test_llm_assistant_cannot_drop_base_detections(self):
        with patch(
            "src.ollama_assistant.call_ollama_generate",
            return_value={
                "requested_sensing": ["temperature"],
                "selected_components": ["AHT20"],
                "unsupported_requirements": [],
                "confidence": "high",
                "notes": ["LLM returned a partial extraction."],
            },
        ):
            parsed, meta = run_ollama_requirement_assistant(
                "room comfort brightness and air freshness, no camera",
                app.SENSOR_LIBRARY,
                app.SUPPORTED_SENSORS,
                app.SENSOR_KEYWORDS,
                app.REQUIREMENT_GROUPS,
                app.REQUIREMENT_CONFIG,
            )

        self.assertEqual(meta["mode"], "ollama")
        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750", "SGP30"])
        self.assertIn("camera", parsed["unsupported_requirements"])
        self.assertTrue(any("Preserved Base assistant" in note for note in meta["notes"]))

    def test_ollama_provider_helpers_support_remote_endpoints_and_auth(self):
        self.assertEqual(get_ollama_provider_label("http://localhost:11434"), "Local Ollama")
        self.assertEqual(get_ollama_provider_label("https://models.example.com"), "Remote Ollama")

        with patch("src.ollama_assistant.OLLAMA_API_KEY", "test-key"), patch(
            "src.ollama_assistant.OLLAMA_AUTH_HEADER",
            "",
        ):
            headers = build_ollama_headers(include_json=True)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Authorization"], "Bearer test-key")

    def test_ollama_timeout_env_is_import_safe(self):
        with patch.dict("os.environ", {"BAD_TIMEOUT": ""}):
            self.assertEqual(read_int_env("BAD_TIMEOUT", 120), 120)
        with patch.dict("os.environ", {"BAD_TIMEOUT": "abc"}):
            self.assertEqual(read_int_env("BAD_TIMEOUT", 120), 120)
        with patch.dict("os.environ", {"BAD_TIMEOUT": "-5"}):
            self.assertEqual(read_int_env("BAD_TIMEOUT", 120), 120)
        with patch.dict("os.environ", {"BAD_TIMEOUT": "30"}):
            self.assertEqual(read_int_env("BAD_TIMEOUT", 120), 30)

    def test_ollama_status_reports_unreachable_remote_server(self):
        status = check_ollama_status(
            model="qwen2.5:3b",
            base_url="http://127.0.0.1:1",
            timeout=1,
        )

        self.assertEqual(status["provider"], "Local Ollama")
        self.assertFalse(status["reachable"])
        self.assertFalse(status["model_available"])
        self.assertTrue(status["error"])

    def test_mode_list_keeps_base_first_and_adds_cloud_options(self):
        self.assertEqual([app.MODE_BASE, app.MODE_OLLAMA, app.MODE_GEMINI], ["Base", "Ollama LLM", "Gemini API"])

    def test_gemini_api_key_prefers_streamlit_secrets_then_environment(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}):
            self.assertEqual(get_gemini_api_key({"GEMINI_API_KEY": "secret-key"}), "secret-key")
            self.assertEqual(get_gemini_api_key({}), "env-key")

    def test_gemini_api_key_handles_missing_streamlit_secrets_file(self):
        class MissingSecrets:
            def get(self, _key, _default=""):
                raise RuntimeError("No secrets files found")

        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            self.assertEqual(get_gemini_api_key(MissingSecrets()), "")

    def test_gemini_status_does_not_expose_key(self):
        status = check_gemini_status({"GEMINI_API_KEY": "secret-key"})

        self.assertTrue(status["api_key_configured"])
        self.assertEqual(status["provider"], "Gemini API")
        self.assertIn("gemini-2.5-flash", status["fallback_models"])
        self.assertNotIn("secret-key", json.dumps(status))

    def test_gemini_model_candidates_are_unique(self):
        candidates = get_gemini_model_candidates("gemini-2.5-flash-lite")

        self.assertEqual(candidates[0], "gemini-2.5-flash-lite")
        self.assertEqual(len(candidates), len(set(candidates)))

    def test_gemini_falls_back_when_api_key_missing(self):
        with patch("src.gemini_assistant.get_gemini_api_key", return_value=""):
            parsed, meta = run_gemini_requirement_assistant(
                "room comfort brightness",
                app.SENSOR_LIBRARY,
                app.SUPPORTED_SENSORS,
                app.SENSOR_KEYWORDS,
                app.REQUIREMENT_GROUPS,
                app.REQUIREMENT_CONFIG,
            )

        self.assertEqual(meta["mode"], "gemini_fallback")
        self.assertEqual(meta["provider"], "Gemini API")
        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750"])
        self.assertEqual(parsed["ai_assistant"]["mode"], "gemini_fallback")

    def test_gemini_validates_output_and_ignores_invented_hardware(self):
        with patch(
            "src.gemini_assistant.call_gemini_generate",
            return_value={
                "requested_sensing": ["temperature", "soil_moisture"],
                "selected_components": ["AHT20", "SOIL999"],
                "unsupported_requirements": ["camera"],
                "confidence": "high",
                "notes": ["Gemini returned an invented component."],
            },
        ):
            parsed, meta = run_gemini_requirement_assistant(
                "temperature with camera",
                app.SENSOR_LIBRARY,
                app.SUPPORTED_SENSORS,
                app.SENSOR_KEYWORDS,
                app.REQUIREMENT_GROUPS,
                app.REQUIREMENT_CONFIG,
                api_key="fake-key",
            )

        self.assertEqual(meta["mode"], "gemini")
        self.assertEqual(parsed["selected_components"], ["AHT20"])
        self.assertNotIn("soil_moisture", parsed["requested_sensing"])
        self.assertIn("camera", parsed["unsupported_requirements"])
        self.assertTrue(any("Ignored unsupported" in note for note in meta["notes"]))

    def test_gemini_preserves_base_detections_when_model_is_partial(self):
        with patch(
            "src.gemini_assistant.call_gemini_generate",
            return_value={
                "requested_sensing": ["temperature"],
                "selected_components": ["AHT20"],
                "unsupported_requirements": [],
                "confidence": "high",
                "notes": ["Gemini returned a partial extraction."],
            },
        ):
            parsed, meta = run_gemini_requirement_assistant(
                "room comfort brightness and air freshness, no camera",
                app.SENSOR_LIBRARY,
                app.SUPPORTED_SENSORS,
                app.SENSOR_KEYWORDS,
                app.REQUIREMENT_GROUPS,
                app.REQUIREMENT_CONFIG,
                api_key="fake-key",
            )

        self.assertEqual(meta["mode"], "gemini")
        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750", "SGP30"])
        self.assertIn("camera", parsed["unsupported_requirements"])
        self.assertTrue(any("Preserved Base assistant" in note for note in meta["notes"]))

    def test_gemini_api_error_falls_back_to_base(self):
        with patch("src.gemini_assistant.call_gemini_generate", side_effect=RuntimeError("quota exceeded")):
            parsed, meta = run_gemini_requirement_assistant(
                "room comfort brightness",
                app.SENSOR_LIBRARY,
                app.SUPPORTED_SENSORS,
                app.SENSOR_KEYWORDS,
                app.REQUIREMENT_GROUPS,
                app.REQUIREMENT_CONFIG,
                api_key="fake-key",
            )

        self.assertEqual(meta["mode"], "gemini_fallback")
        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750"])
        self.assertIn("quota exceeded", meta["fallback_reason"])

    def test_gemini_uses_fallback_model_before_base_fallback(self):
        def fake_generate(_prompt, api_key, model):
            if model == "primary-model":
                raise RuntimeError("temporary demand")
            return {
                "requested_sensing": ["temperature"],
                "selected_components": ["AHT20"],
                "unsupported_requirements": [],
                "confidence": "high",
                "notes": ["Fallback model succeeded."],
            }

        with patch("src.gemini_assistant.call_gemini_generate", side_effect=fake_generate), patch(
            "src.gemini_assistant.GEMINI_MODEL_FALLBACKS",
            ["fallback-model"],
        ):
            parsed, meta = run_gemini_requirement_assistant(
                "temperature",
                app.SENSOR_LIBRARY,
                app.SUPPORTED_SENSORS,
                app.SENSOR_KEYWORDS,
                app.REQUIREMENT_GROUPS,
                app.REQUIREMENT_CONFIG,
                api_key="fake-key",
                model="primary-model",
            )

        self.assertEqual(meta["mode"], "gemini")
        self.assertEqual(meta["model"], "fallback-model")
        self.assertEqual(parsed["selected_components"], ["AHT20"])
        self.assertTrue(any("fallback model" in note.lower() for note in meta["notes"]))

    def test_local_assistant_validation_keeps_output_inside_supported_hardware(self):
        rule_based = app.parse_requirements("room comfort brightness and camera")
        ai_result = {
            "requested_sensing": ["temperature", "humidity", "light", "soil_moisture"],
            "selected_components": ["AHT20", "BH1750", "CAM123"],
            "unsupported_requirements": ["camera"],
            "confidence": "high",
            "notes": ["room comfort mapped to temperature and humidity"],
        }

        parsed, notes = validate_ai_extraction(
            ai_result,
            rule_based,
            app.SENSOR_LIBRARY,
            app.SUPPORTED_SENSORS,
            app.REQUIREMENT_CONFIG,
        )

        self.assertEqual(parsed["selected_components"], ["AHT20", "BH1750"])
        self.assertNotIn("soil_moisture", parsed["requested_sensing"])
        self.assertIn("camera", parsed["unsupported_requirements"])
        self.assertTrue(any("Ignored unsupported" in note for note in notes))

    def test_readiness_review_ready_for_simple_supported_sensor(self):
        package = app.generate_design_package("temperature humidity")
        review = app.generate_design_readiness_review(package)

        self.assertEqual(review["status"], "Ready")
        self.assertEqual(review["blockers"], [])

    def test_readiness_review_needs_review_for_optional_pins(self):
        package = app.generate_design_package("light sensing")
        review = app.generate_design_readiness_review(package)

        self.assertEqual(review["status"], "Needs Review")
        self.assertTrue(any("Optional/configuration pins" in item for item in review["review_items"]))

    def test_readiness_review_blocks_unsupported_or_empty_design(self):
        unsupported_package = app.generate_design_package("temperature with GPS and camera")
        unsupported_review = app.generate_design_readiness_review(unsupported_package)
        empty_package = app.generate_design_package("make a tiny wireless board")
        empty_review = app.generate_design_readiness_review(empty_package)

        self.assertEqual(unsupported_review["status"], "Blocked")
        self.assertEqual(empty_review["status"], "Blocked")

    def test_non_i2c_sensor_gets_validation_warning(self):
        sensor = {
            "component": "SPI123",
            "display_name": "SPI123",
            "order": 50,
            "interface": "SPI",
            "functions": "SPI test",
            "categories": [
                {
                    "name": "spi_test",
                    "function": "SPI test sensing",
                    "keywords": ["spi test"],
                }
            ],
            "linked_categories": [],
            "i2c_address": "0x00",
            "supply": "3.3 V",
            "current_ma": 1.0,
            "footprint": "SPI footprint",
            "pins": {
                "VCC": "3V3",
                "GND": "GND",
                "SDA": "I2C_SDA",
                "SCL": "I2C_SCL",
            },
            "placement": "Place near MCU.",
            "routing": "Review manually.",
        }
        errors, warnings = app.analyze_sensor_definition(sensor, Path("SPI123/sensor.json"))

        self.assertEqual(errors, [])
        self.assertTrue(any("interface SPI" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
