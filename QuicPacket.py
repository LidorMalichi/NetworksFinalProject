import struct

class QUICPacket:

    def __init__(self, flags: int, connection_id: int, packet_number: int, frames: list):
        self.flags = flags
        self.connection_id = connection_id
        self.packet_number = packet_number
        self.frames = frames  # This will hold an instances of StreamFrame

    def serialize(self):
        header = struct.pack('!BQI', self.flags, self.connection_id, self.packet_number)
        payload = b''.join(frame.serialize() for frame in self.frames)
        return header + payload

    @staticmethod
    def deserialize(data):
        flags, connection_id, packet_number = struct.unpack('!BQI', data[:13])
        payload = data[13:]

        frames = []
        while payload:
            frame, payload = StreamFrame.deserialize(payload)
            frames.append(frame)

        return QUICPacket(flags, connection_id, packet_number, frames)


class StreamFrame:
    DATA_FRAME = 0b0001  # Regular data frame
    FIN_DATA_FRAME = 0b0010  # Final (FIN) + data frame

    def __init__(self, stream_id: int, offset: int, length: int, stream_data: bytes, flags: int = DATA_FRAME):
        self.stream_id = stream_id
        self.offset = offset
        self.length = length
        self.stream_data = stream_data
        self.flags = flags

    def is_data_frame(self):
        return self.flags & StreamFrame.DATA_FRAME

    def is_fin_data_frame(self):
        return self.flags & StreamFrame.FIN_DATA_FRAME

    def serialize(self):
        """Serialize the frame data for transmission."""
        header = struct.pack('!BQI', self.flags, self.stream_id, self.offset)
        length = struct.pack('!I', len(self.stream_data))  # Include length in serialization
        return header + length + self.stream_data

    @classmethod
    def deserialize(cls, data: bytes):
        """Deserialize received data into a StreamFrame object."""
        flags, stream_id, offset = struct.unpack('!BQI', data[:13])
        length = struct.unpack('!I', data[13:17])[0]  # Extract length
        stream_data = data[17:17+length]
        remaining_data = data[17+length:]
        return cls(stream_id, offset, length, stream_data, flags), remaining_data
