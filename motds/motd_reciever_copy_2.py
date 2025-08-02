import socket
import select
import time
import json
from machine import RTC #type: ignore
rtc = RTC()
# Setup server socket
def web_setup():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(5)
    s.setblocking(False)
    clients = []  # keep track of open client sockets
    return s, clients
#welcome to indentation hell
def web_server(s, clients):
    # your display logic here (non-blocking)
    # your motor logic here (non-blocking)

    # Check for new incoming connections
    rlist, _, _ = select.select([s], [], [], 0)
    for server_sock in rlist:
        cl, addr = server_sock.accept()
        print('Client connected from', addr)
        cl.setblocking(False)
        clients.append(cl)

    # Check if any client sockets have data to read
    if clients:
        rlist, _, _ = select.select(clients, [], [], 0)
        for cl in rlist:
            try:
                data = cl.recv(1024)
                if not data:
                    # client closed connection
                    cl.close()
                    clients.remove(cl)
                    continue

                request = data.decode()
                print("Request:", request)
                if 'GET /?motd=' in request:
                    query = request.split('GET /?')[1].split(' ')[0]
                    params = query.split('&')
                    for p in params:
                        if p.startswith('motd='):
                            motd = p.split('=')[1].replace('+', ' ').replace('%20', ' ')
                        elif p.startswith('author='):
                            author = p.split('=')[1].replace('+', ' ').replace('%20', ' ')

                    print(f"New data: {motd}, {author}")

                    with open('motds.json', 'r') as f:
                        data = json.load(f)
                        print(data)
                    highest_id_dict = data[-1]
                    highest_id = highest_id_dict["id"]
                    new_id = highest_id + 1

                    now = rtc.datetime()
                    newdata = {
                        "motd": motd,
                        "id": new_id,
                        "author": author,
                        "time": now,
                        "new": True
                    }
                    
                    data.append(newdata)

                    with open('motds.json', 'w') as f:
                        json.dump(data, f)
                    
                    print("saved the new data")
                    cl.send(b'HTTP/1.0 200 OK\r\n\r\nMotd Recieved')
                    cl.close()
                    clients.remove(cl)
                    
                    return newdata

                elif 'GET /motds.json' in request:
                    with open('motds.json', 'r') as f:
                        data = json.load(f)

                    response_body = json.dumps(data)
                    cl.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                    cl.send(response_body)
                    cl.close()
                    continue
                               
                else:
                    cl.send(b'HTTP/1.0 200 OK\r\n\r\nDeault response')
                    cl.close()
                    clients.remove(cl)

            except Exception as e:
                print("client error:", e)
                cl.close()
                clients.remove(cl)

if __name__ == '__main__':
    a, b = web_setup()
    while True:
        web_server(a, b)