from machine import ADC, Pin
import config
adc = ADC(Pin(config.bat_adc))

def read_bat_voltage():
    reading = adc.read_u16()  # 16-bit value (0-65535)
    voltage = 2 * reading * 3.3 / 65535
    return voltage