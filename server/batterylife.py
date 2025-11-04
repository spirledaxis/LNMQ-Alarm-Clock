import time
import requests
start = time.time()
counter = 0
timeouts = 0
while True:
    try:
        print("requesting...", end=' ')
        requests.get('http://192.168.1.51/status.json', timeout=10) 
    except requests.exceptions.ConnectionError:
        print("clock went down")
        end = time.time()
        with open('batterylife.txt', 'w') as f:
            f.write(f'{end-start}\ntimeouts: {timeouts}')
        break
    except requests.exceptions.Timeout:
        print("timeout")
        timeouts += 1
    else:
        counter += 1
        print(f"Connected to pico! ({counter})")
        time.sleep(5)