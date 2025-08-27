import socket
import json

HOST = "0.0.0.0"   # Listen on all interfaces
PORT = 8080        # Port to listen on
JSON_FILE = "motds_cache.json"  # The JSON file you want to serve

def load_json():
    with open(JSON_FILE, "r") as f:
        return f.read()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print(f"Server running on http://{HOST}:{PORT}")

        while True:
            client_socket, addr = server_socket.accept()
            with client_socket:
                request = client_socket.recv(1024).decode("utf-8")
                if not request:
                    continue

                # Parse HTTP request line
                request_line = request.splitlines()[0]
                method, path, _ = request_line.split()

                if method == "GET" and path == "/data.json":
                    body = load_json()
                    print("serving json")
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        f"{body}"
                    )
                else:
                    body = json.dumps({"error": "Not found"})
                    response = (
                        "HTTP/1.1 404 Not Found\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        f"{body}"
                    )

                client_socket.sendall(response.encode("utf-8"))

if __name__ == "__main__":
    start_server()
