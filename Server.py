import time
from Quic import QUICProtocol
from Events import *

def run_server(host='127.0.0.1', port=12345):
    server = QUICProtocol(is_client=False)
    server.bind(host, port)
    print(f"Server listening on {host}:{port}")

    server.accept_connection()

    while True:
        server.recv()  # Process incoming packets

        while not server.events.empty():
            event = server.events.get()
            if isinstance(event, StreamRequestEvent):
                num_streams = event.num_streams
                print(f"Preparing to send {num_streams} streams to client.")

                for stream_id in range(1, num_streams + 1):
                    data = b'Stream data for stream ' + bytes([stream_id])
                    server.send(stream_id, data, end_of_stream=True)

        time.sleep(0.1)  # Slight delay to avoid CPU overload

    server.close()

if __name__ == '__main__':
    run_server()
