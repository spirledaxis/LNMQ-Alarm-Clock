import schedule
import time
import requests
import json
from datetime import datetime
def main():
    try:
        motds = requests.get('http://192.168.1.51/motds.json')
    except Exception as e:
        print('failed', e)
        
        now = datetime.now().strftime("%-H:%M:%S %-m/%-d/%Y")
        with open('backuplog.log', 'a') as f:
            f.write(f'{e}\n{now}\n')
    else:
        motds = motds.content.decode("utf-8")
        print(motds)
        motds = json.loads(motds)
        with open('motdsbackup.json', 'w') as f:
            print("writing...")
            json.dump(motds, f)

        now = datetime.now().strftime("%-H:%M:%S %-m/%-d/%Y")
        with open('backuplog.log', 'a') as f:
            f.write(f'Backup Success at {now}\n')

schedule.every().hour.do(main)
while True:
    schedule.run_pending()
    time.sleep(1)