import _thread
import errno
import json
import time

import utime
from machine import PWM, Pin

from lib.neotimer import Neotimer


class HeadLights:
    def __init__(self, left_pin, right_pin, pwm_freq, max_brightness=1):
        raise DeprecationWarning("Use HeadLightsStream instead")
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
            time.sleep_us(500)

    def _set_duty(self, strength):
        """Apply PWM duty to both headlights"""
        duty = int(strength * 65535)
        self.left_light.duty_u16(duty)
        self.right_light.duty_u16(duty)
