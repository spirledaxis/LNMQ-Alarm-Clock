from .home import Home
from .display_off import DisplayOff
from .messageviewer import MessageViewer
from .setalarm import SetAlarm
from . import aliases
from lib import XglcdFont
print("loading fonts...")
timefont = XglcdFont('fonts/Proxy24x31.bin', 24, 31)
bally = XglcdFont('fonts/Bally7x9.bin', 7, 9)
bally_mini = XglcdFont('fonts/Bally5x8.bin', 5, 8)
__all__ = ["Home", "DisplayOff", "MessageViewer", "SetAlarm", "aliases", "timefont", "bally", "bally_mini"]
