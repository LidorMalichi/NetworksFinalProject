class Event:
    """Base class for events."""
    pass

class StreamDataReceived(Event):
    def __init__(self, stream_id, data, end_of_stream):
        self.stream_id = stream_id
        self.data = data
        self.end_of_stream = end_of_stream

class ACKReceived(Event):
    def __init__(self, packet_number):
        self.packet_number = packet_number

class StreamRequestEvent(Event):
    def __init__(self, num_streams):
        self.num_streams = num_streams
