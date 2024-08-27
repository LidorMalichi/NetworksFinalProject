import time
import random
from Quic import QUICProtocol
from Events import *


def run_server(host='127.0.0.1', port=4433):
    server = QUICProtocol(is_client=False)
    server.bind(host, port)
    print(f"Server listening on {host}:{port}")

    server.accept_connection()

    # Load the content of the file to send
    with open('toSend.txt', 'rb') as file:
        file_data = file.read()

    # Create dictionaries to track the remaining data and chunk size for each stream
    remaining_data_per_stream = {}
    chunk_size_per_stream = {}
    streams_remaining = set()

    while True:
        server.recv()  # Process incoming packets

        while not server.events.empty():
            event = server.events.get()
            if isinstance(event, StreamRequestEvent):
                num_streams = event.num_streams
                print(f"Preparing to send {num_streams} streams to client.")

                # Initialize dictionaries for each stream
                for stream_id in range(1, num_streams + 1):
                    remaining_data_per_stream[stream_id] = file_data[:]
                    chunk_size_per_stream[stream_id] = random.randint(1000, 2000)
                    print(f"Stream {stream_id} using chunk size: {chunk_size_per_stream[stream_id]}")

                # Continue sending data until all streams are done
                streams_remaining = set(range(1, num_streams + 1))

                while streams_remaining:
                    stream_id = random.choice(list(streams_remaining))
                    data_chunk = remaining_data_per_stream[stream_id]

                    if data_chunk:
                        # Use the pre-sampled chunk size for this stream
                        chunk_size = chunk_size_per_stream[stream_id]

                        chunk = data_chunk[:chunk_size]
                        remaining_data_per_stream[stream_id] = data_chunk[chunk_size:]

                        end_of_stream = len(remaining_data_per_stream[stream_id]) == 0
                        server.send(stream_id, chunk, end_of_stream=end_of_stream)

                        if end_of_stream:
                            print(f"Stream {stream_id} has finished sending.")
                            streams_remaining.remove(stream_id)
                    else:
                        streams_remaining.remove(stream_id)

        if not streams_remaining:
            print("All streams have been sent. Closing server.")
            break

        time.sleep(0.1)  # Slight delay to avoid CPU overload

    server.close()


if __name__ == '__main__':
    run_server()
