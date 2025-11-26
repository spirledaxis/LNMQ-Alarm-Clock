import os

src = fr"audio\pulsepatterns"
files = os.listdir(src)
for f in files:
    cmd = f'mpremote cp {src}/{f} :/pulsepatterns/'
    os.system(cmd)
