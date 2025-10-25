import ujson as json
from machine import PWM, Pin  # type: ignore
import time


def stream_pattern(filename):
    """
    Stream elements from a JSON array like:
    [[0.0, 0.0], [20.0, 0.1], [50.0, 0.31], ...]
    """
    with open(filename, 'r') as f:
        depth = 0
        buf = ''
        while True:
            c = f.read(1)
            if not c:
                break  # EOF

            if c == '[':
                depth += 1
                if depth == 2:   # entering a [t, s] pair
                    buf = '['
            elif c == ']':
                if depth == 2:   # finished a pair
                    buf += ']'
                    try:
                        yield json.loads(buf)
                    except Exception as e:
                        print("Parse error:", e)
                    buf = ''
                depth -= 1
            elif depth == 2:
                buf += c
        # end while


# setup PWM
led = PWM(Pin(3))
led.freq(1000)

prev_t, prev_strength = None, None
total_time = 0

# countdown
print("Going soon")
for i in range(3):
    print(3 - i)
    time.sleep(1)
print("Go!")

for t, strength in stream_pattern('4.json'):
    if prev_t is not None:
        t_diff = t - prev_t
        total_time += t_diff
        led.duty_u16(int(prev_strength * 65535))
        time.sleep_ms(int(t_diff))
    prev_t, prev_strength = t, strength

print("Total duration:", total_time)
led.duty_u16(0)
