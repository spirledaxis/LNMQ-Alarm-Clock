from machine import I2C, Pin
i2c = I2C(0, sda=Pin(16), scl=Pin(17))
print(i2c.scan())
