from machine import I2C, Pin
import time
# straight from Mr.GPT, idk how accurate it is
# TODO: look at adafruits circutpython and mirror it in micro
# TMP117 default I2C address
TMP117_ADDR = 0x48
TMP117_TEMP_REG = 0x00

# Initialize I2C (adjust pins and bus as needed)
i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=400000)


def read_tmp117_temp():
    # Read 2 bytes from temperature register
    data = i2c.readfrom_mem(TMP117_ADDR, TMP117_TEMP_REG, 2)

    # Combine high and low bytes
    raw_temp = (data[0] << 8) | data[1]

    # Handle negative temperatures (2's complement, 16-bit)
    if raw_temp & 0x8000:
        raw_temp -= 1 << 16

    # Each LSB = 7.8125e-3 °C
    temp_c = raw_temp * 0.0078125
    f = (temp_c * 9 / 5) + 32
    return f
