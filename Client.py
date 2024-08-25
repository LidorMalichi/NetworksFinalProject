from Quic import QUICProtocol
from Events import *

def run_client(host='127.0.0.1', port=12345, num_streams=5):
    client = QUICProtocol(is_client=True)
    client.connect(host, port)

    client.send_stream_request(num_streams)

    while True:
        client.recv()  # Process incoming packets

        while not client.events.empty():
            event = client.events.get()
            if isinstance(event, StreamDataReceived):
                print(f"Received data on stream {event.stream_id}: {event.data}")

        if len(client.fin_streams) >= num_streams:
            break  # Exit if all streams are finished

    client.close()

if __name__ == '__main__':
    run_client(num_streams=3)
