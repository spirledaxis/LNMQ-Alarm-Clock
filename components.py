from lib.neotimer import Neotimer
from machine import Pin, PWM #type: ignore
from lib.neotimer import Neotimer

class Alarm:
    def __init__(self, hour, minute, callback):
        """use military time for the hour"""
        self.hour = hour
        self.minute = minute
        self.callback_func = callback
        self.cooldown = False #cooldown logic so it doesn't go off for the entire minute
        self.cooldown_timer = Neotimer(0)
    def update(self, now):
        """checks if the time matches, then does the callback
        Args:
            now: a rtc tuple"""
        #(year, month, mday, hour, minute, second, weekday, yearday)

        now_hour = now[4]
        now_minute = now[5]

        if now_hour == self.hour and now_minute == self.minute and not self.cooldown:
            print("alarm should go off now")
            self.callback_func()
            self.cooldown = True 
            self.cooldown_timer = Neotimer(70_000)
            self.cooldown_timer.start()

        if self.cooldown_timer.finished():
            self.cooldown = False

        else:
            print("still on cooldown")

class Button:
    def __init__(self, pin, callback, debounce_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.callback_func = callback
        self.debounce_timer = Neotimer(debounce_ms)
        self.state = 0
        self.prev_state = 0
        self.is_debounced = False
        self.press_counter = 0
    def update(self):
        if self.debounce_timer.debounce_signal(not self.pin.value()):
            self.is_debounced = True

        if self.pin.value() == 0: #the pull up resistor inverts the signal, pressed reads as 0
            self.state = 1 #self.state and prev_state use 0 as not pressed, opposite to pin.value
        else:
            self.state = 0

        if (self.state == 0 and self.prev_state == 1):
            if self.is_debounced:
                self.callback_func()
                print(self.press_counter, end = ' ')
                self.press_counter += 1
            else:
                print("under debounce cooldown")
            
            self.is_debounced = False

        self.prev_state = self.state
        
class Switch:
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)

    def state(self):
        if self.pin.value() == 0:
            return True
        else:
            return False

class Motor:
    def __init__(self, left_pin, right_pin, pwm_freq):
        self.left_pin = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_pin = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.is_idle = False
        self.movement_increment = 0
        self.timer = Neotimer(-1)
    def _interact(self, cmd, speed):
        print("interacting...")
        #speed to duty cycle (speed param is percentage)
        duty_cycle = int((65535*speed) / 100)

        if cmd == 'l':
            self.left_pin.duty_u16(duty_cycle)
            self.right_pin.duty_u16(0)
        elif cmd == 'r':
            self.left_pin.duty_u16(0)
            self.right_pin.duty_u16(duty_cycle)
        elif cmd == 'w':
           self.left_pin.duty_u16(0)
           self.right_pin.duty_u16(0)
    
        self.is_idle = False
      
    def do_movement(self, movement):
        print("doing movement...")
        self.movements = movement
        cmd, dur_ms, speed = movement[self.movement_increment]
        self.timer = Neotimer(dur_ms)
        self.timer.start()
        print(f"started timer with {dur_ms}")
        self._interact(cmd, speed)
        
    def movement_len_ms(self, movement):
        time_ms = 0
        for _, dur_ms, _, in movement:
            time_ms += dur_ms
        
        return time_ms
    
    def stop(self):
        print("stopping...")
        self.left_pin.duty_u16(0)
        self.right_pin.duty_u16(0)
        self.is_idle = True
        
    def update(self):
        if self.is_idle:
            return

