from .button import Button, RepeatButton
from .headlights import HeadLightsStream as HeadLights
from .motor import Motor
from .switch import Switch
from .picodfplayer import DFPlayer
from .ssd1309 import Display
import config
from machine import SPI, Pin #type: ignore

spi = SPI(config.spi_channel_disp, baudrate=5_000_000, sck=Pin(config.sck), mosi=Pin(config.sda))
display = Display(spi, dc=Pin(config.dc), cs=Pin(config.cs), rst=Pin(config.res), offscreen_warnings=False, flip=True)
headlights = HeadLights(config.headlight_l, config.headlight_r, config.headlights_pwm_freq, config.max_brightness)
speaker = DFPlayer(config.uarto_channel_df, config.tx, config.rx, config.busy, config.transistor)
motor = Motor(config.motor_l, config.motor_r, config.motor_pwm_freq, config.motor_min_pwm)
switch = Switch(config.switch, debounce_ms=100)

