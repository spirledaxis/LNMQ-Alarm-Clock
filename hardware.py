from lib.neotimer import Neotimer
from machine import Pin, PWM  # type: ignore
from lib.neotimer import Neotimer
import json
from lib import timeutils
from utime import sleep_ms
from movements import *
import errno
from time import sleep_us
import _thread
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
        """
        HeadLights controller
        cmd syntax: ('light', effect, dur)
        """
        self.left_light = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_light = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.max_brightness = max_brightness
        self.stop()  # initialize state

    def stop(self):
        """Stop any running pattern and reset state"""
        self.left_light.duty_u16(0)
        self.right_light.duty_u16(0)
        self.ready = False
        self.pulse_pattern = None
        self.increment = 0
        self.max_increment = -1
        self.timer = Neotimer(0)
        self.timer.start()  # start a zero-duration timer to avoid errors

    def start(self, ringtone):
        """Load a pulse pattern and start the lights"""
        self._set_pulse_pattern_by_ringtone(ringtone)
        self.ready = True
        self.increment = 0  # always start at the beginning

    def headlight_thread_step(self):
        """Call repeatedly to step through the light pattern"""
        if self.ready:
            self._run_pattern()

    def _set_pulse_pattern_by_ringtone(self, ringtone):
        """Load pulse pattern from JSON file"""
        try:
            with open(f"pulsepatterns/{ringtone}.json", 'r') as f:
                self.pulse_pattern = json.load(f)
                self.max_increment = len(self.pulse_pattern) - 1
                print("found pulsepattern")
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("no pulsepattern found, using default")
                self.pulse_pattern = [[5000, 1.0]]  # always a list of lists
                self.max_increment = 0

    def _run_pattern(self):
        """Execute the next step in the pulse pattern"""
        if self.increment > self.max_increment:
            self.stop()
            return

        if self.timer.finished():
            # handle first element separately
            if self.increment == 0:
                waitfor = self.pulse_pattern[0][0]
                strength = self.pulse_pattern[0][1]
            else:
                waitfor = self.pulse_pattern[self.increment][0] - \
                          self.pulse_pattern[self.increment - 1][0]
                strength = self.pulse_pattern[self.increment - 1][1]

            # clamp strength to max_brightness
            if strength > self.max_brightness:
                strength = self.max_brightness

            # set PWM duty
            self.left_light.duty_u16(int(strength * 65535))
            self.right_light.duty_u16(int(strength * 65535))

            # advance to next step
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

import ujson as json
from machine import PWM, Pin  # type: ignore
import time


class HeadLightsStream:
    """
    Stream-based headlights controller.
    Streams pulse patterns directly from JSON files without loading them fully.
    JSON format example:
      [[0.0, 0.0], [20.0, 0.1], [50.0, 0.31], ...]
    """

    def __init__(self, left_pin, right_pin, pwm_freq=1000, max_brightness=1.0):
        self.left_light = PWM(Pin(left_pin))
        self.right_light = PWM(Pin(right_pin))
        self.left_light.freq(pwm_freq)
        self.right_light.freq(pwm_freq)
        self.max_brightness = max_brightness
        self.active = False
        self.pattern_gen = None
        self.prev_t = None
        self.prev_strength = None
        self.stop_thread = False
    def stop(self):
        """Stop headlights output"""
        print("attempted to stop lightshow")
        self.active = False
        self.left_light.duty_u16(0)
        self.right_light.duty_u16(0)
        self.pattern_gen = None
        self.prev_t = None
        self.prev_strength = None
        self.stop_thread = True
    def start(self, filename):
        """Begin streaming a pattern from a JSON file"""
        try:
            self.pattern_gen = self._stream_pattern(filename)
            self.active = True
            self.prev_t = None
            self.prev_strength = None
        except OSError:
            print("Pattern file not found, using fallback")
            self.pattern_gen = iter([[0, 1.0], [5000, 0.0]])  # fallback
            self.active = True
        self.stop_thread = False
        _thread.start_new_thread(self.headlight_thread, ())

    def _stream_pattern(self, filename):
        """Generator that yields [t, s] pairs from a JSON array file"""
        with open(filename, 'r') as f:
            depth = 0
            buf = ''
            while True:
                c = f.read(1)
                if not c:
                    break  # EOF

                if c == '[':
                    depth += 1
                    if depth == 2:  # entering a [t, s] pair
                        buf = '['
                elif c == ']':
                    if depth == 2:  # finished a pair
                        buf += ']'
                        try:
                            yield json.loads(buf)
                        except Exception as e:
                            print("Parse error:", e)
                        buf = ''
                    depth -= 1
                elif depth == 2:
                    buf += c

    def run(self):
        """
        Streams the pattern in real time.
        Can be interrupted by setting self.active = False.
        """
        if not self.active or not self.pattern_gen:
            return

        try:
            while self.active:
                try:
                    t, strength = next(self.pattern_gen)
                except StopIteration:
                    break  # pattern finished

                # compute time since last step
                if self.prev_t is None:
                    t_diff = 0
                else:
                    t_diff = t - self.prev_t

                # clamp brightness
                strength = max(0, min(strength, self.max_brightness))

                # update PWM
                self._set_duty(strength)

                # small-sleep loop so stop() can interrupt
                start = time.ticks_ms()
                while self.active and time.ticks_diff(time.ticks_ms(), start) < t_diff:
                    time.sleep_ms(10)

                # update previous
                self.prev_t, self.prev_strength = t, strength

        finally:
            # ensure lights are off
            self._set_duty(0)
            self.stop()

    def headlight_thread(self):
        while not self.stop_thread:
            self.run()
            sleep_us(500)

    
    def _set_duty(self, strength):
        """Apply PWM duty to both headlights"""
        duty = int(strength * 65535)
        self.left_light.duty_u16(duty)
        self.right_light.duty_u16(duty)


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
