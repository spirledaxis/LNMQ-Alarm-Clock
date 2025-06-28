#In order ror this example-code to work, make sure you have a
#card with at least one folder, containing at least two mp3:s.
#The folders should be named 01, 02 etc and files should be named
#001.mp3, 002.mp3 etc.
from utime import sleep_ms, sleep
from picodfplayer import DFPlayer
from machine import Pin

#Constants. Change these if DFPlayer is connected to other pins.
UART_INSTANCE=0
TX_PIN = 12
RX_PIN = 13
BUSY_PIN = 16
mybusypin = Pin(16, Pin.IN, Pin.PULL_UP)

#Create player instance
player=DFPlayer(UART_INSTANCE, TX_PIN, RX_PIN, BUSY_PIN)

#Check if player is busy.
print(mybusypin.value())
#Play the first song (001.mp3) from the first folder (01)

print('Playing track 001.mp3 in folder 01')
player.playTrack(1,1)
sleep(0.2)
print('Playing?', player.queryBusy())
print(mybusypin.value())
#Wait 5 seconds...
sleep(5)
#Pause
print('Pausing')


player.pause()
print('Playing?', player.queryBusy())
#Wait 2 seconds...
sleep(2)

#Resume
print('Resuming play')
player.resume()

#Wait 5 seconds
sleep(5)

#Next Track
print('Skipping to next track')
player.nextTrack()

#Wait 5 seconds
sleep(5)

#Pause by directly sending the pause  (0x0E) command to the command line and printing the output.
print('Pausing by sending the pause command manually, and printing the output')
print(str(player.sendcmd(0x0E, 0x00, 0x00)))

print('You can try me out by sending commands in the console, such as player.resume()')