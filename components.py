from lib.neotimer import Neotimer
from machine import Pin, PWM #type: ignore
from lib.neotimer import Neotimer
import config
from lib.picodfplayer import DFPlayer
from displaystates import display
class Motor:
    def __init__(self, left_pin, right_pin, pwm_freq):
        self.left_pin = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_pin = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.is_idle = True
        self.ready = False
        self.movement_increment = -1
        self.timer = Neotimer(0)
    
    def _interact(self, cmd, speed):
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
    
    def set_movement(self, movement):
        """A movement is a list of tuples.
        Syntax: (cmd, dur_ms, speed)
        cmd: 'l', 'r', or 'w' (wait)
        dur_ms: duration of that cmd
        speed: a percent of the motors speed
        """
        self.movement = movement
        self.timer.start()
        self.ready = True

    def do_movement(self):
        if not self.ready:
            return
        
        if self.timer.finished():
            if self.movement_increment + 1 >= len(self.movement): 
                print("end of movement")
                self.movement_increment = -1

            else:
                self.movement_increment += 1
                cmd, dur_ms, speed = self.movement[self.movement_increment]
                self.timer = Neotimer(dur_ms)
                self.timer.start()
                self._interact(cmd, speed)       

    def movement_len_ms(self, movement):
        time_ms = 0
        for _, dur_ms, _, in movement:
            time_ms += dur_ms
        
        return time_ms
    
    def stop(self):
        print("stopping motor")
        self.left_pin.duty_u16(0)
        self.right_pin.duty_u16(0)
        self.is_idle = True
        self.ready = False
        self.timer = Neotimer(0)
        self.timer.start()
        self.movement_increment = -1

    def start(self):
        self.ready = True

class Alarm:
    def __init__(self, hour, minute, motor_movement, ringtone, motor, speaker):
        """use military time for the hour. """
        self.hour = hour
        self.minute = minute
        self.motor_movement = motor_movement
        self.ringtone = ringtone
        self.cooldown = False #cooldown logic so it doesn't go off for the entire minute
        self.cooldown_timer = Neotimer(0)
        self.alarm_restart_timer = Neotimer(1000)
        self.is_active = False
        self.motor = motor
        self.speaker = speaker
      
    def update(self, now):
        """
        Args:
            now: a rtc tuple"""
        #(year, month, mday, hour, minute, second, weekday, yearday)

        now_hour = now[4]
        now_minute = now[5]

        if now_hour == self.hour and now_minute == self.minute and not self.cooldown:
            display.wake()
            print("alarm should go off now")
            self.cooldown = True 
            self.cooldown_timer = Neotimer(70_000)
            self.cooldown_timer.start()
            self.is_active = True
            self.speaker.playTrack(1, self.ringtone)
            self.motor.set_movement(self.motor_movement)
   
        if self.cooldown_timer.finished():
            self.cooldown = False
 
        if self.is_active:
            if not self.speaker.queryBusy():  
                print("going at it again")
                self.motor.stop() #stop the motor in the case that the movement is longer than the audio
                self.speaker.playTrack(1, self.ringtone)
                self.motor.start()
            self.motor.do_movement()

    def stop(self):
        print("stopping...")
        if not self.is_active:
            print("attempted to stop alarm, but none was active")
        
        self.speaker.pause()
        self.motor.stop()
        self.is_active = False

    def fire(self):
        "Use this to fire the alarm whenever. Bypasses cooldown, and doesn't repeat."
        self.is_active = True
        print("firing...")
       
    def edit_time(self, hour, minute):
        "change when the alarm object will fire"
        self.hour = hour
        self.minute = minute
       
    def edit_ringtone(self, ringtone:int):
        self.ringtone = ringtone

    def edit_motor_movement(self, movement):
        self.motor_movement = movement
        
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
    def __init__(self, pin, debounce_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.debounce_timer = Neotimer(debounce_ms)
        self.state = False
        self.stable_state = False
        self.lock = False

    def update(self):

        if self.pin.value() == 0:
            self.state = True
        else:
            self.state = False
    
        if self.state != self.stable_state and not self.lock:
            self.debounce_timer.start()
            self.lock = True

        if self.debounce_timer.finished():
            self.debounce_timer.reset()
            self.stable_state = self.state
            self.lock = False

            if self.stable_state == self.state:
                print("debounced false input")
    
    def get_state(self):
        return self.stable_state
    
if __name__ == '__main__':
    print('ehlo')
    from machine import RTC
    rtc = RTC()
    now = rtc.datetime()
    hour = now[4]
    minute = now[5]
    from utime import sleep
    motor = Motor(config.motor_l, config.motor_r, 2000)
    custom_movement = [
    ('l', 20000, 85),    # move left for 0.8s at 85% speed
    ('r', 800, 85),
    ('r', 400, 85),
]
    exciting_movement = [
    ('r', 400, 100),  # quick burst right at full speed
    ('l', 400, 100),  # quick burst left at full speed
    ('r', 300, 100),  # shorter burst right
    ('l', 300, 100),  # shorter burst left
    ('w', 200, 0),    # brief pause
    ('r', 600, 80),   # longer slide right at slightly lower speed
    ('l', 600, 80),   # longer slide left
    ('w', 100, 0),    # quick pause
    ('r', 200, 100),  # quick snap right
    ('l', 200, 100),  # quick snap left
    ('w', 300, 0),    # pause before finish
    ('r', 500, 90),   # final strong move right
    ('l', 500, 90)    # final strong move left
]

    timer = Neotimer(2000)
    speaker = DFPlayer(config.uarto_channel_df, config.tx, config.rx, config.busy, config.transistor)
    alarm = Alarm(hour, minute, exciting_movement, 13, motor, speaker)
    try:
        while True:
            alarm.update(now)
    finally:
        motor.stop()
        speaker.cleanup()
