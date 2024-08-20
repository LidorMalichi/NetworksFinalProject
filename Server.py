import socket
import random
from Packet import StreamFrame, QUICPacket


def create_dummy_file(size_in_mb):
    return b'a' * (size_in_mb * 1024 * 1024)  # 2 MB of dummy data


def udp_server(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))

    # Receive the number of files the client wants
    data, client_address = sock.recvfrom(1024)
    num_files = int(data.decode())
    print(f"Client requested {num_files} files")

    # Create the files and streams
    files = {i: create_dummy_file(2) for i in range(num_files)}
    stream_frame_sizes = {stream_id: random.randint(1000, 2000) for stream_id in files.keys()}
    stream_offsets = {stream_id: 0 for stream_id in files.keys()}
    streams_completed = set()

    # Send acknowledgment for the handshake
    sock.sendto(b'ACK', client_address)
    print(f"Sent ACK to client for handshake")

    # Wait for acknowledgment from client
    data, _ = sock.recvfrom(1024)
    if data == b'ACK':
        print("Received ACK from client, starting file transfer")

    # File transfer phase
    while len(streams_completed) < len(files):
        selected_streams = random.sample([stream_id for stream_id in files.keys() if stream_id not in streams_completed], 3)
        frames = []

        for stream_id in selected_streams:
            frame_size = stream_frame_sizes[stream_id]
            data = files[stream_id][stream_offsets[stream_id]:stream_offsets[stream_id] + frame_size]
            if not data:
                streams_completed.add(stream_id)
                continue

            offset = stream_offsets[stream_id]
            frames.append(StreamFrame(stream_id, offset, len(data), data))
            stream_offsets[stream_id] += len(data)

        if frames:
            packet = QUICPacket(flags=0b0001, connection_id=12345, packet_number=random.randint(1, 100000), frames=frames)
            sock.sendto(packet.serialize(), client_address)

    print("File transfer completed")
    sock.close()


if __name__ == "__main__":
    udp_server('localhost', 9999)
