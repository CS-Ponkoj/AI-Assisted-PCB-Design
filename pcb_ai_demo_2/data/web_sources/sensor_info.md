### AHT20 – temperature and humidity sensor

The AHT20 is a new generation of temperature and humidity sensor that outputs
calibrated digital signals over a standard I²C interface.  The datasheet
explains that the AHT20 includes a dedicated ASIC and MEMS sensor and arrives
fully calibrated so no external calibration is required【764409156739556†L4-L15】.  Key
features include a digital output with excellent long‑term stability, a small
SMD package suitable for reflow soldering and a quick response with strong
anti‑jamming capability【764409156739556†L23-L29】.

### BH1750 – ambient light sensor

The BH1750 is a 16‑bit ambient light sensor used for detecting the amount of
light in an environment.  Adafruit’s product guide notes that it is small,
capable and inexpensive and is useful for determining whether to adjust
display brightness or detect day versus night【47281359819431†L197-L205】.  The sensor
provides 16‑bit measurements in lux (the SI unit for illuminance) with a
measurement range from 0 to over 65 k lux【47281359819431†L209-L214】.  It communicates
using the I²C bus, making it easy to integrate with microcontrollers【47281359819431†L218-L224】.

### SGP30 – air quality sensor

The SGP30 is a fully integrated metal‑oxide (MOX) gas sensor that combines
multiple sensing elements on one chip to provide detailed air‑quality
information.  It is designed to detect a wide range of volatile organic
compounds (VOCs) and hydrogen (H₂) for indoor air quality monitoring【927352169341937†L158-L167】.
The sensor returns total VOC (TVOC) readings and equivalent carbon‑dioxide
(eCO₂) values via its I²C interface and has a typical accuracy of about 15 %【927352169341937†L158-L167】.

### BMP280 – barometric pressure sensor

Bosch’s BMP280 is a precision barometric pressure and temperature sensor.
Adafruit describes it as a low‑cost, precision solution with ±1 hPa absolute
pressure accuracy and ±1 °C temperature accuracy and notes that it can also
serve as an altimeter with ±1 m accuracy【300816700879662†L213-L217】.  The BMP280 is
the successor to earlier Bosch pressure sensors and can communicate over
either the I²C or SPI bus【300816700879662†L219-L223】.  For simple wiring, I²C is
recommended【300816700879662†L219-L223】.