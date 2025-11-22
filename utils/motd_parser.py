import json
import random


def fetch_data():
    with open('motds.json') as f:
        data: list = json.load(f)

    return data


def id_search(data, id):
    return data[id - 1]


def author_search(data, author):
    results = []
    for i in data:
        if i['author'] == author:
            results.append(i)

    return results


def date_search_range(data, timestamp1, timestamp2):
    results = []
    for i in data:
        timestamp = i['time']

        if timestamp1 <= timestamp and timestamp <= timestamp2:
            results.append(i)

    return results


def date_search(data, timestamp, greater_less):
    results = []
    for i in data:
        if greater_less == '>' and i['time'] > timestamp:
            results.append(i)

        elif greater_less == '<' and i['time'] < timestamp:
            results.append(i)

        else:
            raise ValueError("must be > or <")

    return results


def select_random_motd(data):
    r = random.randint(1, len(data))
    motd = id_search(data, r)
    print(motd)
    return motd

def select_random_motd_queue(queue: list):
    if len(queue) > 1:
        r = random.randint(0, len(queue)-1)
    else:
        print("theres only 1 element left")
        r = 0
    print(f"selecting from {queue} with index {r} (len = {len(queue)})")
    motd = queue[r]
    queue.pop(r)
    return motd, queue
