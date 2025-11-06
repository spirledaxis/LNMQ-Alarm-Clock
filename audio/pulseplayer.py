import time

import ujson as json
from machine import PWM, Pin  # type: ignore

with open('pattern.json', 'r') as f:
    pattern = json.load(f)

print("Going soon")
for i in range(3):
    print(3 - i)
    time.sleep(1)
print("Go!")
# 14
led = PWM(Pin(14))  # change to your GPIO
led.freq(1000)      # 1 kHz PWM
sum = 0
for i in range(1, len(pattern)):
    t_diff = pattern[i][0] - pattern[i - 1][0]
    sum += t_diff
print(sum)
for i in range(1, len(pattern)):
    current_strength = pattern[i - 1][1]
    # time difference in your units (assume ms)
    t_diff = pattern[i][0] - pattern[i - 1][0]

    # Apply current strength
    led.duty_u16(int(current_strength * 65535))

    # Wait for the difference
    time.sleep_ms(int(t_diff))  # convert ms to seconds if your time is in ms

led.duty_u16(0)
