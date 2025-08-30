from machine import SPI, Pin #type: ignore
from lib.ssd1309 import Display

from lib.picodfplayer import DFPlayer
from lib.neotimer import Neotimer
#motor
motor_l = 19
motor_r = 18
motor_pwm_freq = 20_000
motor_min_pwm = 37_000

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

#timers
display_timeout_min = 0.25
display_messenger_timeout_min = 0.5
messenger_cycle_time_s = 30
messenger_icon_cycle_time_s = 10
alarm_timeout_min = 5
bsod_timeout_s = 5
display_timer = Neotimer(display_timeout_min*60_000) 

#other
ip = '192.168.1.51'
server_ip = '192.168.1.21'
server_port = 8080