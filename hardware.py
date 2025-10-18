from lib.neotimer import Neotimer
from machine import Pin, PWM  # type: ignore
from lib.neotimer import Neotimer
import json
from lib import timeutils
from utime import sleep_ms
from movements import *


class Motor:
    def __init__(self, left_pin, right_pin, pwm_freq, min_pwm):
        "cmd sytax: ('dir', time_ms, %speed)"
        self.left_pin = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_pin = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.is_idle = True
        self.ready = False
        self.movement_increment = -1
        self.timer = Neotimer(0)
        self.min_pwm = min_pwm
        self.max_pwm = 65535
        self.repeat = False

    def _interact(self, cmd, speed_percent):
        # speed to duty cycle (speed param is percentage)
        speed_percent = max(0, min(speed_percent, 100))
        # Linear interpolation
        duty_cycle = int(self.min_pwm + (speed_percent / 100)
                         * (self.max_pwm - self.min_pwm))

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

    def do_movement(self):
        if not self.ready:
            return

        if self.timer.finished():
            if self.movement_increment + 1 >= len(self.movement):
                print("end of movement")
                if not self.repeat:
                    self.stop()
                self.movement_increment = -1

            else:
                self.movement_increment += 1
                cmd, dur_ms, speed = self.movement[self.movement_increment]
                self.timer = Neotimer(dur_ms)
                self.timer.start()
                self._interact(cmd, speed)

    def motor_thread_step(self):
        if self.ready:
            self.do_movement()

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

    def start(self, reset_increment=False):
        self.ready = True
        if reset_increment:
            self.movement_increment = -1

    def set_movement_by_ringtone(self, ringtone):
        self.repeat = False
        if ringtone == 13:
            self.set_movement(freedom_dive)
        elif ringtone == 8:
            self.set_movement(i_am_speed)
        elif ringtone == 19:
            self.set_movement(eta)
        elif ringtone == 17:
            self.set_movement(stay_with_me)
        elif ringtone == 18:
            self.set_movement(clash_royale)
        else:
            self.set_movement(default)
            self.repeat = True


class HeadLights:
    def __init__(self, left_pin, right_pin, pwm_freq, max_brightness=1):
        "cmd syntax: ('light', effect, dur)"
        self.left_light = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_light = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.max_brightness = max_brightness
        self.stop()

    def stop(self):
        self.ready = False
        self.pulse_pattern = None
        self.increment = 1
        self.max_increment = -1
        self.timer = Neotimer(0)
        self.timer.finished = True

    def headlight_thread_step(self):
        if self.ready:
            self._run_pattern()

    def start(self, ringtone):
        self.ready = True
        self._set_pulse_pattern_by_ringtone(ringtone)

    def _set_pulse_pattern_by_ringtone(self, ringtone):
        try:
            with open(f"pulsepatterns/{ringtone}.json", 'r') as f:
                self.pulse_pattern = json.load(f)
                self.max_increment = len(self.pulse_pattern)
        except FileNotFoundError:
            self.pulse_pattern = [0.0, 0.0]
            self.max_increment = 1

    def _run_pattern(self):
        if self.increment > self.max_increment:
            self.stop()

        if self.timer.finished():
            waitfor = self.pulse_pattern[self.increment][0] - \
                self.pulse_pattern[self.increment - 1][0]
            strength = self.pulse_pattern[self.increment - 1][1]
            if strength > self.max_brightness:
                strength = self.max_brightness

            self.left_light.duty_u16(int(strength * 65535))
            self.right_light.duty_u16(int(strength * 65535))
            self.increment += 1
            self.timer = Neotimer(waitfor)
            self.timer.start()


class Button:
    def __init__(self, pin, callback, debounce_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.callback_func = callback
        self.debounce_timer = Neotimer(debounce_ms)
        self.state = 0
        self.prev_state = 0
        self.is_debounced = False
        self.pressed = False

    def update(self):
        if self.debounce_timer.debounce_signal(not self.pin.value()):
            self.is_debounced = True

        if self.pin.value() == 0:  # the pull up resistor inverts the signal, pressed reads as 0
            self.state = 1  # self.state and prev_state use 1 as pressed, opposite to pin.value
        else:
            self.state = 0

        if (self.state == 1 and self.prev_state == 0):
            if self.is_debounced:
                self.pressed = True
                self.callback_func()
            else:
                print("under debounce cooldown")

            self.is_debounced = False

        else:
            self.pressed = False

        self.prev_state = self.state


class RepeatButton(Button):
    def __init__(self, pin, callback, init_delay_ms=200, repeat_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.callback_func = callback
        self.init_delay = Neotimer(init_delay_ms)
        self.repeat_ms = Neotimer(repeat_ms)
        self.pressed = False

    def update_state(self):
        if self.pin.value() == 0:  # the pull up resistor inverts the signal, pressed reads as 0
            self.state = 1  # self.state and prev_state use 1 as pressed, opposite to pin.value
        else:
            self.state = 0

    def update(self):
        self.update_state()
        if self.init_delay.hold_signal(
                self.state) and self.repeat_ms.repeat_execution() and self.state == 1:
            self.callback_func()

        if self.state == 1:
            self.pressed = True
        else:
            self.pressed = False


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
