import create_pattern
import parser
import os

import os

# Set the directory you want to scan
directory = "ringtones"

# Get a list of all files in the directory
files = os.listdir(directory)


# Print all filenames
for f in files:
    print(f)
    create_pattern.create_pattern(f)

files = os.listdir("audio_bands")

for f in files:
    parser.create_pulsepattern(f"audio_bands/{f}", 2, f"pulsepatterns/{f.split('.')[0]}")

