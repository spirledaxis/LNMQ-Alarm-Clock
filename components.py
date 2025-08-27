from lib.neotimer import Neotimer
from machine import Pin, PWM #type: ignore
from lib.neotimer import Neotimer
import config
import json
from lib import timeutils
from movements import *
class Motor:
    def __init__(self, left_pin, right_pin, pwm_freq, min_pwm):
        self.left_pin = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_pin = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.is_idle = True
        self.ready = False
        self.movement_increment = -1
        self.timer = Neotimer(0)
        self.min_pwm = min_pwm
        self.max_pwm = 65535
    def _interact(self, cmd, speed_percent):
        #speed to duty cycle (speed param is percentage)
        speed_percent = max(0, min(speed_percent, 100))
        # Linear interpolation
        duty_cycle = int(self.min_pwm + (speed_percent / 100) * (self.max_pwm - self.min_pwm))

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
    def __init__(self, timeout_s, motor, speaker, switch):
        """use military time for the hour. """
        with open('alarms.json', 'r') as f:
            alarm = json.load(f)
            alarm = alarm[0]
            alarm_hour = int(alarm['hour'])
            alarm_ampm = alarm['ampm']
            self.minute = int(alarm['minute'])
            self.ringtone = alarm['ringtone']
            
        self.hour = timeutils.to_military_time(alarm_hour, alarm_ampm)
        self.timeout_timer = Neotimer(timeout_s*1000)
        self.enabled = switch.get_state()
        self.switch = switch
        self.is_active = False
        self.locked = False #used so alarm logic doesn't go off for the entire minute
        self.motor = motor
        self.speaker = speaker
        self.set_movement_by_ringtone()
        
    def set_movement_by_ringtone(self):
        if self.ringtone == 13:
            self.motor.set_movement(freedom_dive)
        elif self.ringtone == 8:
            self.motor.set_movement(i_am_speed)
        else:
            self.motor.set_movement(custom_movement)

    def update(self, now):
        """
        Args:
            now: a rtc tuple"""
        #(year, month, mday, hour, minute, second, weekday, yearday)
        self.switch.update()
        if self.switch.get_state():
            self.enabled = True
        else:
            print("switch is off")
            self.enabled = False
            
        now_hour = now[4]
        now_minute = now[5]
        print(self.hour, self.minute, self.locked, self.enabled)
        if now_hour == self.hour and now_minute == self.minute and not self.locked and self.enabled:
            self.fire()
            print("firing")
        
        elif now_hour != self.hour and now_minute != self.minute and self.locked:
            self.locked = False

        if self.timeout_timer.finished():
            print("timeout reached")
            self.stop()

        if self.is_active:
            if not self.speaker.queryBusy():  
                print("going at it again")
                self.motor.stop() #stop the motor in the case that the movement is longer than the audio
                self.speaker.playTrack(1, self.ringtone)
                self.motor.start()
            self.motor.do_movement()
    
    def fire(self):
        if self.locked:
            return
        
        print("alarm should go off now")
        self.locked = True
        self.is_active = True
        config.display_timer.reset()
        config.display.wake()

        self.speaker.playTrack(1, self.ringtone)
        #self.motor.set_movement(self.motor_movement)
        self.timeout_timer.start()

    def stop(self):
        print("stopping...")
        if not self.is_active:
            print("attempted to stop alarm, but none was active")
        
        self.speaker.pause()
        self.motor.stop()
        self.timeout_timer.stop()
        self.timeout_timer.reset()
        self.is_active = False

class Button:
    def __init__(self, pin, callback, debounce_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.callback_func = callback
        self.debounce_timer = Neotimer(debounce_ms)
        self.state = 0
        self.prev_state = 0
        self.is_debounced = False
        self.press_counter = 0
        self.pressed = False

    def update(self):
        if self.debounce_timer.debounce_signal(not self.pin.value()):
            self.is_debounced = True

        if self.pin.value() == 0: #the pull up resistor inverts the signal, pressed reads as 0
            self.state = 1 #self.state and prev_state use 0 as not pressed, opposite to pin.value
        else:
            self.state = 0

        if (self.state == 0 and self.prev_state == 1):
            if self.is_debounced:
                self.pressed = True
                self.callback_func()
                print(self.press_counter, end = ' ')
                self.press_counter += 1
            else:
                print("under debounce cooldown")
                
            self.is_debounced = False

        else:
            self.pressed = False
            
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
    from machine import RTC #type: ignore
    motor = Motor(config.motor_l, config.motor_r, config.motor_pwm_freq, config.motor_min_pwm)
    switch = Switch(config.switch)
    myalarm = Alarm(config.alarm_timeout_min * 60, motor, config.speaker, switch)
    rtc = RTC()
    now = rtc.datetime()
    myalarm.minute = now[5]
    myalarm.hour = now[4]
    myalarm.enabled = True
    myalarm.ringtone = 8
    print("yo")
    switch = Switch(config.switch)
    try:
        while True:
            switch.update()
            myalarm.update(now)
    finally:
        motor.stop()
        config.speaker.cleanup()
        config.display.cleanup()
