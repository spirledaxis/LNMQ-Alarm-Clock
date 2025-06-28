from machine import Pin, I2C
import ssd1306
from utime import sleep

i2c = I2C(0, sda=Pin(16), scl=Pin(17))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

try:
    display.fill(0)  # Clear screen
    display.text("Hello World", 0, 0)
    display.show()
    sleep(2)
    display.fill(1)
    display.show()
    sleep(2)
finally:
    print("clearing display")
    display.fill(0)
    display.show()