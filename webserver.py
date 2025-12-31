import json
import select
import socket
from machine import RTC

rtc = RTC()


def web_setup():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80))
    s.listen(3)  # keep it low — microcontrollers hate many connections
    s.setblocking(False)

    clients = []   # list of open client sockets
    return s, clients


def close_client(cl, clients):
    """Safely close and remove client socket."""
    try:
        cl.close()
    except:
        pass
    try:
        clients.remove(cl)
    except:
        pass


def send_response(cl, body, content_type="text/plain"):
    """Send HTTP response with Connection: close."""
    try:
        header = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        cl.send(header)
        if isinstance(body, str):
            cl.send(body)
        else:
            cl.send(body)
    except:
        pass


def web_server(s, clients, status_json):
    """Handle incoming HTTP requests safely."""

    # --- Accept new incoming connections ---
    try:
        rlist, _, _ = select.select([s], [], [], 0)
    except:
        rlist = []

    for srv in rlist:
        try:
            cl, addr = srv.accept()
            cl.setblocking(False)
            clients.append(cl)
            print("Client connected:", addr)
        except:
            pass

    if not clients:
        return None

    # --- Handle client sockets ---
    try:
        rlist, _, _ = select.select(clients, [], [], 0)
    except MemoryError:
        # Too many sockets → close everything
        print("MemoryError: clearing clients")
        for c in clients[:]:
            close_client(c, clients)
        return None
    except:
        return None

    for cl in rlist:

        try:
            data = cl.recv(1024)
        except:
            close_client(cl, clients)
            continue

        # No data → closed or dead
        if not data:
            close_client(cl, clients)
            continue

        # Decode request
        try:
            request = data.decode()
        except:
            close_client(cl, clients)
            continue

        print("REQ:", request)

        # --- ROUTES -------------------------------------------------------

        # /?motd=x&author=y
        if "GET /?motd=" in request:
            try:
                query = request.split("GET /?")[1].split(" ")[0]
                params = query.split("&")

                motd = ""
                author = ""

                for p in params:
                    if p.startswith("motd="):
                        motd = p[5:].replace("+", " ").replace("%20", " ").replace("%3D", "=")
                    elif p.startswith("author="):
                        author = p[7:].replace("+", " ").replace("%20", " ")

                with open("motds.json", "r") as f:
                    arr = json.load(f)

                new_id = arr[-1]["id"] + 1
                now = rtc.datetime()

                new_entry = {
                    "motd": motd,
                    "id": new_id,
                    "author": author,
                    "time": now,
                    "new": True
                }

                arr.append(new_entry)

                with open("motds.json", "w") as f:
                    json.dump(arr, f)

                send_response(cl, "Motd Received")
                close_client(cl, clients)
                return ("motd", new_entry)

            except Exception as e:
                print("ERR motd:", e)
                close_client(cl, clients)
                return None

        # /motds.json
        if "GET /motds.json" in request:
            try:
                with open("motds.json", "r") as f:
                    arr = json.load(f)

                send_response(cl, json.dumps(arr), "application/json")
            except:
                send_response(cl, "[]", "application/json")

            close_client(cl, clients)
            continue

        # /status.json
        if "GET /status.json" in request:
            send_response(cl, status_json, "application/json")
            close_client(cl, clients)
            continue

        # /?alarm_msg=x
        if "GET /?alarm_msg=" in request:
            try:
                query = request.split("GET /?")[1].split(" ")[0]
                params = query.split("&")

                for p in params:
                    if p.startswith("alarm_msg="):
                        msg = p[len("alarm_msg="):].replace("+", " ").replace("%20", " ")

                        with open("alarm.json", "r") as f:
                            j = json.load(f)

                        j["alarm_message"] = msg

                        with open("alarm.json", "w") as f:
                            json.dump(j, f)

                        send_response(cl, "Alarm Message Saved")
                        close_client(cl, clients)
                        return ("alarm_msg", msg)

            except Exception as e:
                print("ERR alarm:", e)

            close_client(cl, clients)
            return None
        if "GET /toggle_disp" in request:
            send_response(cl, "Toggled Display")
            close_client(cl, clients)
            return ("toggle_disp", -1)
        # --- Default route ---
        send_response(cl, "Default response")
        close_client(cl, clients)

    return None
