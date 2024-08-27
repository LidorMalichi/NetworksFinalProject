from Quic import QUICProtocol
from Events import *
import time


def run_client(host='127.0.0.1', port=1234):
    num_streams = int(input("Enter the number of streams: "))

    client = QUICProtocol(is_client=True)
    client.connect(host, port)

    client.send_stream_request(num_streams)

    # Dictionary to hold statistics for each stream
    stream_stats = {stream_id: {'bytes_received': 0, 'frames_received': 0, 'start_time': time.time()} for stream_id in
                    range(1, num_streams + 1)}

    while True:
        client.recv()  # Process incoming packets

        while not client.events.empty():
            event = client.events.get()
            if isinstance(event, StreamDataReceived):
                stream_id = event.stream_id
                stream_stats[stream_id]['bytes_received'] += len(event.data)
                stream_stats[stream_id]['frames_received'] += 1

                if event.end_of_stream:
                    stream_stats[stream_id]['end_time'] = time.time()

        if len(client.fin_streams) >= num_streams:
            # Calculate statistics for each stream
            for stream_id, stats in stream_stats.items():
                end_time = stats.get('end_time', time.time())
                duration = end_time - stats['start_time']
                data_rate = stats['bytes_received'] / duration if duration > 0 else 0
                frame_rate = stats['frames_received'] / duration if duration > 0 else 0
                print(f"\nStream #{stream_id}:")
                print(f"\tBytes received: {stats['bytes_received']}")
                print(f"\tFrames received: {stats['frames_received']}")
                print(f"\tData rate: {data_rate:.2f} bytes/second")
                print(f"\tFrame rate: {frame_rate:.2f} frames/second")

            # Calculate overall statistics
            total_bytes_received = sum(stats['bytes_received'] for stats in stream_stats.values())
            total_frames_received = sum(stats['frames_received'] for stats in stream_stats.values())
            total_duration = max(
                stats.get('end_time', time.time()) - stats['start_time'] for stats in stream_stats.values())
            average_data_rate = total_bytes_received / total_duration if total_duration > 0 else 0
            average_frame_rate = total_frames_received / total_duration if total_duration > 0 else 0

            print("\nOverall statistics:")
            print(f"\tTotal bytes received: {total_bytes_received}")
            print(f"\tTotal frames received: {total_frames_received}")
            print(f"\tAverage data rate: {average_data_rate:.2f} bytes/second")
            print(f"\tAverage frame rate: {average_frame_rate:.2f} frames/second")

            break  # Exit if all streams are finished

    client.close()


if __name__ == '__main__':
    run_client()
