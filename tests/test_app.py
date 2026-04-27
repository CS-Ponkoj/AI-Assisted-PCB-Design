import json
import tempfile
import unittest
from pathlib import Path

import app


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
