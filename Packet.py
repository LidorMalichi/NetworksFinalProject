import struct


class StreamFrame:
    def __init__(self, stream_id, offset, length, stream_data):
        self.stream_id = stream_id
        self.offset = offset
        self.length = length
        self.stream_data = stream_data

    def serialize(self):
        frame_header = struct.pack('!III', self.stream_id, self.offset, self.length)
        return frame_header + self.stream_data

    @staticmethod
    def deserialize(data):
        stream_id, offset, length = struct.unpack('!III', data[:12])
        stream_data = data[12:12 + length]
        return StreamFrame(stream_id, offset, length, stream_data)


class QUICPacket:
    def __init__(self, flags, connection_id, packet_number, frames):
        self.flags = flags
        self.connection_id = connection_id
        self.packet_number = packet_number
        self.frames = frames

    def serialize(self):
        header = struct.pack('!BQI', self.flags, self.connection_id, self.packet_number)
        payload = b''.join(frame.serialize() for frame in self.frames)
        return header + payload

    @staticmethod
    def deserialize(data):
        flags, connection_id, packet_number = struct.unpack('!BQI', data[:13])
        frames_data = data[13:]
        frames = []

        while frames_data:
            stream_id, offset, length = struct.unpack('!III', frames_data[:12])
            stream_data = frames_data[12:12 + length]
            frame = StreamFrame(stream_id, offset, length, stream_data)
            frames.append(frame)
            frames_data = frames_data[12 + length:]

        return QUICPacket(flags, connection_id, packet_number, frames)
