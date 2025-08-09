from machine import SPI, Pin #type: ignore
from lib.ssd1309 import Display
from components import Motor
from lib.picodfplayer import DFPlayer

#motor
motor_l = 19
motor_r = 18
motor = Motor(motor_l, motor_r, 20_000, 37000)

#dfplayer
rx = 17
tx = 16
transistor = 21
busy = 20
uarto_channel_df = 0
speaker = DFPlayer(uarto_channel_df, tx, rx, busy, transistor)
#display
"""
pins from gnd-cs
gnd
vcc
sck
sda
res
dc
cs
"""
sck = 14
sda = 15
res = 13
dc = 12
cs = 11 
spi_channel_disp = 1

spi = SPI(spi_channel_disp, baudrate=10_000_000, sck=Pin(sck), mosi=Pin(sda))
display = Display(spi, dc=Pin(dc), cs=Pin(cs), rst=Pin(res), offscreen_warnings=False, flip=True)

#inputs
snd_fx_l = 8 #these are also paired
#right wire fell off, idc enough to solder it on. Thus, use the left one
snd_fx_r = 2
snze_l = 4 #the snze buttons seems to be paired
snze_r = 3 #so, you can use either (but not both!)
alm_set = 0
clk_set = 1
fwd = 7
rev = 9
switch = 6

#other
ip = '192.168.1.51'
display_timeout_min = 3
alarm_timeout_min = 5