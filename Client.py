import socket
import time
from Packet import QUICPacket


def udp_client(host, port, num_files):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Start handshake and send the number of files requested
    sock.sendto(str(num_files).encode(), (host, port))

    # Wait for acknowledgment from server
    data, server_address = sock.recvfrom(1024)
    if data == b'ACK':
        print("Received ACK from server for handshake")

        # Send acknowledgment back to server
        sock.sendto(b'ACK', server_address)
        print("Sent ACK to server, ready to receive files")

    stream_statistics = {i: {'bytes': 0, 'frames': 0} for i in range(num_files)}
    start_time = time.time()

    # File reception phase
    while True:
        data, _ = sock.recvfrom(4096)
        if not data:
            break

        packet = QUICPacket.deserialize(data)
        for frame in packet.frames:
            stream_id = frame.stream_id
            stream_data = frame.stream_data

            # Update statistics
            stream_statistics[stream_id]['bytes'] += len(stream_data)
            stream_statistics[stream_id]['frames'] += 1

        # Check if all streams are completed
        if all(stat['bytes'] >= 2 * 1024 * 1024 for stat in stream_statistics.values()):
            break

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate and print statistics
    for stream_id, stats in stream_statistics.items():
        bytes_per_sec = stats['bytes'] / total_time
        frames_per_sec = stats['frames'] / total_time
        print(f"Stream {stream_id}:")
        print(f"  Bytes received: {stats['bytes']}")
        print(f"  Frames received: {stats['frames']}")
        print(f"  Avg bytes/sec: {bytes_per_sec:.2f}")
        print(f"  Avg frames/sec: {frames_per_sec:.2f}")

    total_bytes = sum(stats['bytes'] for stats in stream_statistics.values())
    total_frames = sum(stats['frames'] for stats in stream_statistics.values())
    avg_bytes_per_sec = total_bytes / total_time
    avg_frames_per_sec = total_frames / total_time

    print("\nOverall statistics:")
    print(f"  Total bytes received: {total_bytes}")
    print(f"  Total frames received: {total_frames}")
    print(f"  Avg bytes/sec: {avg_bytes_per_sec:.2f}")
    print(f"  Avg frames/sec: {avg_frames_per_sec:.2f}")

    sock.close()


if __name__ == "__main__":
    num_files = int(input("Enter the number of files to request (1-10): "))
    udp_client('localhost', 9999, num_files)
