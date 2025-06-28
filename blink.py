from machine import Pin
from utime import sleep

pin = Pin(16, Pin.OUT)
trans = Pin(17, Pin.OUT)
trans.on()
print("LED starts flashing...")
while True:
    try:
        trans.toggle()
        sleep(1) # sleep 1sec
    except KeyboardInterrupt:
        break
pin.off()
print("Finished.")
