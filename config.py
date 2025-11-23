# motor
motor_l = 19
motor_r = 18
motor_pwm_freq = 20_000
motor_min_pwm = 37_000


# headlights
headlight_l = 22
headlight_r = 3
headlights_pwm_freq = 1000
max_brightness = 1  # value from 0 to 1

# dfplayer
rx = 17
tx = 16
transistor = 21
busy = 20
uarto_channel_df = 0


# display
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


# temperature
tmp_scl = 27
tmp_sda = 26

# inputs
snd_fx_l = 8  # these are also paired
snd_fx_r = 2  # right wire fell off, idc enough to solder it on. Thus, use the left one
snze_l = 4  # the snze buttons seems to be paired
snze_r = 3  # so, you can use either (but not both!)
alm_set = 0
clk_set = 1
fwd = 7
rev = 9
switch = 6

# timers
display_timeout_min = 10
display_messenger_timeout_min = 360
messenger_cycle_time_s = 30
messenger_icon_invert_time_s = 10
messenger_drift_inverval_ms = 15_000
alarm_timeout_min = 5
bsod_timeout_s = 15
blink_nowifi_ms = 200

# ips
server_ip = '192.168.1.21'
server_port = 8080

# other
blink_wifi_max = 5
sleep_offset_min = 20
bat_adc = 28
msg_scroll_speed = 1
snooze_min = 10
scroll_on_fwd = 64
first_of_month_index = 25
