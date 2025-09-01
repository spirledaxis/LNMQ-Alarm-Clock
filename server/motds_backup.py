import requests
import json
from datetime import datetime
# to be run by crontab
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
    with open('motdsbackup.json', 'r') as f:
        data = json.load(f)

    backup_len = len(data)
    current_len = len(motds)
    if current_len > backup_len:
        with open('motdsbackuplong.json', 'w') as f:
            json.dump(motds, f)

    with open('motdsbackup.json', 'w') as f:
        print("writing...")
        json.dump(motds, f)

    now = datetime.now().strftime("%-H:%M:%S %-m/%-d/%Y")
    with open('backuplog.log', 'a') as f:
        f.write(f'Backup Success at {now}\n')
