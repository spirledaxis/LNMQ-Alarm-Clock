from machine import ADC, Pin
import config
import framebuf
adc = ADC(Pin(config.bat_adc))
def make_icon(data, x=8, y=8):
    return framebuf.FrameBuffer(bytearray(data), x, y, framebuf.MONO_VLSB)

battery_critical = make_icon(
    [0x00, 0x7f, 0x40, 0xfb, 0xfb, 0x40, 0x7f, 0x00])
battery_full = make_icon(
    [0x00, 0x7f, 0x7f, 0xff, 0xff, 0x7f, 0x7f, 0x00])
battery_L1 = make_icon(
    [0x00, 0x7f, 0x47, 0xc7, 0xc7, 0x47, 0x7f, 0x00])
battery_L2 = make_icon(
    [0x00, 0x7f, 0x47, 0xc7, 0xc7, 0x47, 0x7f, 0x00])
battery_L3 = make_icon(
    [0x00, 0x7f, 0x4f, 0xcf, 0xcf, 0x4f, 0x7f, 0x00])
battery_L4 = make_icon(
    [0x00, 0x7f, 0x5f, 0xdf, 0xdf, 0x5f, 0x7f, 0x00])

def read_bat_voltage():
    reading = adc.read_u16()  # 16-bit value (0-65535)
    voltage = 2 * reading * 3.3 / 65535
    return voltage

def get_bat_sprite():
    v_battery = read_bat_voltage()
    if v_battery >= 4.17:
       return battery_full
    elif v_battery >= 4.08:
        return battery_L4
    elif v_battery >= 4.00:
        return battery_L3
    elif v_battery >= 3.92:
        return battery_L2   
    elif v_battery >= 3.83:
        return battery_L1
    else:
        return battery_critical
            