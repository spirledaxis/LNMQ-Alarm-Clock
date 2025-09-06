
import socket
import time
import asyncio
from kasa import Discover, SmartPlug
from creds import username, password


async def toggle_lights():
    dev = await Discover.discover_single("192.168.1.74", username=username, password=password)
    await dev.update()
    dev_info = dev.state_information
    state = bool(dev_info['State'])
    print(state)
    if state == True:
        await dev.turn_off()
    elif state == False:
        await dev.turn_on()
    else:
        print("cooked")

    await dev.update()

addr = socket.getaddrinfo('0.0.0.0', 8080)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
s.settimeout(1)

try:
    while True:
        try:
            cl, addr = s.accept()
        except socket.timeout:
            continue

        print('Client connected from', addr)
        request = cl.recv(1024).decode('utf-8')
        print('Request:', request)

        if 'GET /toggle_light' in request:
            body = 'toggled light'
            try:
                asyncio.run(toggle_lights())
                response = (
                    'HTTP/1.1 200 OK\r\n'
                    'Content-Type: text/plain\r\n'
                    f'Content-Length: {len(body)}\r\n'
                    'Connection: close\r\n'
                    '\r\n'
                    f'{body}'
                )
            except Exception as e:
                body = str(e)
                response = (
                    'HTTP/1.1 500 Internal Server Error\r\n'
                    'Content-Type: text/plain\r\n'
                    f'Content-Length: {len(body)}\r\n'
                    'Connection: close\r\n'
                    '\r\n'
                    f'{body}'
                )

            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

        elif 'GET /clear_cache' in request:
            body = 'cleared cache'
            with open('motds_cache.json', 'w') as f:
                f.write('[]')

            response = (
                'HTTP/1.1 500 Internal Server Error\r\n'
                'Content-Type: text/plain\r\n'
                f'Content-Length: {len(body)}\r\n'
                'Connection: close\r\n'
                '\r\n'
                f'{body}'
            )

            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

        elif 'GET /fetch_cache' in request:
            with open('motds_cache.json', 'r') as f:
                body = f.read()

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n"
                "\r\n"
                f"{body}"
            )
            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()
        elif 'GET /clear_alarm_msg' in request:
            with open('alarm_message_cache.txt', 'w') as f:
                f.write('')

            body = 'cleared alarm message cache'
            response = (
                'HTTP/1.1 200 OK\r\n'
                'Content-Type: text/plain\r\n'
                f'Content-Length: {len(body)}\r\n'
                'Connection: close\r\n'
                '\r\n'
                f'{body}'
            )
            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

        elif 'GET /fetch_alarm_msg' in request:
            with open('alarm_message_cache.txt', 'r') as f:
                body = f.read()

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n"
                "\r\n"
                f"{body}"
            )
            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

        else:
            # For other requests, respond 404 and close
            body = '404 Not Found'
            response = (
                'HTTP/1.1 404 Not Found\r\n'
                'Content-Type: text/plain\r\n'
                f'Content-Length: {len(body)}\r\n'
                'Connection: close\r\n'
                '\r\n'
                f'{body}'
            )
            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

finally:
    s.close()
