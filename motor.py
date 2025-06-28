from machine import Pin, PWM
from utime import sleep

pin1 = PWM(Pin(16), freq=2000, duty_u16=0)
pin2 = PWM(Pin(17), freq=2000, duty_u16=0)

try:
    while True:
        print("Forward")
        pin1.duty_u16(int(65535))
        sleep(2)
        pin1.duty_u16(0)
        sleep(0.1)

        print("Reverse")
        pin2.duty_u16(int(65535))
        sleep(2)
        pin2.duty_u16(0)
        sleep(0.1)
except KeyboardInterrupt:
    pass

# Stop the motor
pin1.duty_u16(0)
pin2.duty_u16(0)
print("Finished.")
