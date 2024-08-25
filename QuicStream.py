from QuicPacket import StreamFrame
from Events import *

class QuicStreamSender:
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.offset = 0

    def send_data(self, data: bytes, end_of_stream: bool = False) -> StreamFrame:
        flags = StreamFrame.DATA_FRAME
        if end_of_stream:
            flags |= StreamFrame.FIN_DATA_FRAME
        frame = StreamFrame(self.stream_id, self.offset, len(data), data, flags)
        self.offset += len(data)
        return frame


class QuicStreamReceiver:
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.received_data = b""  # Buffer to store received data

    def receive_stream_frame(self, stream_frame: StreamFrame):
        """Receive a StreamFrame and generate a StreamDataReceived event."""

        # Process the received data
        self.received_data += stream_frame.stream_data
        
        end_of_stream = False

        if stream_frame.flags & StreamFrame.FIN_DATA_FRAME:
            end_of_stream = True

        # Create a StreamDataReceived event
        event = StreamDataReceived(
            stream_id=self.stream_id,
            data=stream_frame.stream_data,
            end_of_stream=end_of_stream
        )

        # Return the event (you can also trigger an event handler here if needed)
        return event


class QUICStream:
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.sender = QuicStreamSender(stream_id)
        self.receiver = QuicStreamReceiver(stream_id)
        self.is_open = True  # Indicates if the stream is open

    def close(self):
        """Closes the stream."""
        self.is_open = False
