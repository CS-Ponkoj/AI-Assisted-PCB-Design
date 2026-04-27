# Sensor Plugin Schema

Each supported sensor lives in its own folder:

```text
data/sensors/
  SENSOR_NAME/
    sensor.json
```

The app scans every `*/sensor.json` file at startup. A sensor with
`"enabled": false` is validated and shown in the validation panel, but it is not
offered as a supported sensor.

Use `data/sensors/TEMPLATE_SENSOR/sensor.json` as a copyable starting point.

## Required Fields

```json
{
  "component": "SENSOR_PART",
  "display_name": "Sensor Display Name",
  "order": 50,
  "interface": "I2C",
  "functions": "Human-readable sensing function",
  "categories": [
    {
      "name": "requirement_name",
      "function": "Requirement description",
      "keywords": ["words", "the", "user", "may", "type"]
    }
  ],
  "linked_categories": [],
  "i2c_address": "0x00",
  "supply": "3.3 V",
  "current_ma": 1.0,
  "footprint": "Package or footprint guidance",
  "pins": {
    "VCC": "3V3",
    "GND": "GND",
    "SDA": "I2C_SDA",
    "SCL": "I2C_SCL"
  },
  "placement": "PCB placement guidance",
  "routing": "PCB routing guidance"
}
```

## Optional Fields

```json
{
  "enabled": true,
  "visual": {
    "ref": "U7",
    "x": 620,
    "y": 480,
    "w": 138,
    "h": 72,
    "purpose": "Short label",
    "placement": "Short visual note"
  }
}
```

If `visual` is omitted, the app auto-places the footprint in the PCB visual.

## Linked Categories

Use `linked_categories` when one physical sensor satisfies multiple user
requirements. For example, AHT20 links `temperature` and `humidity`, so asking
for either one installs one AHT20 and reports both capabilities.

## Pin Rules

The prototype is optimized for 3.3 V I2C sensors. The validator expects these
nets for fully automatic output:

```json
{
  "VCC": "3V3",
  "GND": "GND",
  "SDA": "I2C_SDA",
  "SCL": "I2C_SCL"
}
```

Optional extra pins are allowed and appear in the pin map. Examples:

```json
{
  "INT": "GPIO_INT_OPTIONAL",
  "EN": "3V3",
  "ADDR": "GND",
  "CS": "3V3"
}
```

Pins that connect to non-standard nets, such as `GPIO_INT_OPTIONAL`, also appear
as extra sensor nets in the netlist so the designer can review them.

If `interface` is not `I2C`, the app shows a warning because the fixed board
architecture and diagrams are still I2C-focused.
