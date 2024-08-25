import socket
import random
from QuicPacket import QUICPacket
from QuicPacket import StreamFrame
from QuicStream import *
from queue import Queue
from Events import *

class QUICProtocol:

    STREAM_REQUEST_FLAG = 0b000001
    STREAM_DATA_FLAG = 0b000010
    ACK_FLAG = 0b000100
    START_CONNECTION_FLAG = 0b001000
    FIN_FLAG = 0b010000
    FIN_ACK_FLAG = 0b100000

    def __init__(self, is_client: bool):
        self.is_client = is_client
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = None  # This will be set later based on client/server role
        self.connection_id = None  # Connection ID to be set upon connection
        self.stream_frame_queue = Queue()
        self.streams = {}  # Tracks streams by their ID
        self.events = Queue() # Queue for stream data recieved events
        self.packet_number = 0  # Initialize packet number
        self.packets_to_ack = {} # Packets to ack
        self.fin_streams = set()  # Tracks streams that have finished sending



    def bind(self, host: str, port: int):
        """Bind the socket to a specific address and port if acting as a server."""
        if self.is_client:
            raise ValueError("Clients cannot bind to a specific address and port.")
        self.socket.bind((host, port))



    def connect(self, host: str, port: int):
        """Set the address for the server if acting as a client and store the connection ID."""
        if not self.is_client:
            raise ValueError("Servers cannot connect to a specific address and port.")
        self.address = (host, port)

        # Send the start connection packet with START_CONNECTION_FLAG
        start_packet = QUICPacket(
            flags=self.START_CONNECTION_FLAG,
            connection_id=0,  # No connection ID yet
            packet_number=self.packet_number,
            frames=[]
        )
        self.socket.sendto(start_packet.serialize(), self.address)

        # Receive the server's response
        data, addr = self.socket.recvfrom(65535)
        response_packet = QUICPacket.deserialize(data)

        # Check if it's a start connection packet and update the connection ID
        if response_packet.flags == self.START_CONNECTION_FLAG:
            self.connection_id = response_packet.connection_id
            print(f"Connection established with ID: {self.connection_id}")

            # Send an ACK back to the server with the updated connection ID
            self.send_ack(response_packet.packet_number)
            print("Acknowledgment sent to the server.")
        else:
            print("Failed to establish connection: unexpected response.")



    def accept_connection(self):
        """Accept a connection request and send a connection ID to the client."""
        data, addr = self.socket.recvfrom(65535)
        packet = QUICPacket.deserialize(data)
        
        if packet.flags == self.START_CONNECTION_FLAG:

            self.connection_id = random.randint(1, 1 << 32)
            print(f"Generated connection ID: {self.connection_id}")
            self.address = addr

            # Send a start connection packet with the connection ID
            start_packet = QUICPacket(
                flags=self.START_CONNECTION_FLAG, 
                connection_id=self.connection_id, 
                packet_number=self.packet_number + 1,
                frames=[]
            )
            self.socket.sendto(start_packet.serialize(), self.address)
            print("Connection ID sent to the client.")

            # Wait for the client's ACK
            data, addr = self.socket.recvfrom(65535)
            client_ack_packet = QUICPacket.deserialize(data)

            # Check if the received packet is an ACK with the correct connection ID
            if client_ack_packet.flags == self.ACK_FLAG and client_ack_packet.connection_id == self.connection_id:
                print(f"Client acknowledged the connection with ID: {self.connection_id}")
            else:
                print("Failed to receive valid acknowledgment from the client.")
        else:
            print("Received unexpected packet during connection process.")


    def send_stream_request(self, num_streams: int):
        """Client sends a request to the server for the desired number of streams/files."""
        request_packet = QUICPacket(
            flags=self.STREAM_REQUEST_FLAG,
            connection_id=self.connection_id,
            packet_number=self.packet_number,
            frames=[StreamFrame(stream_id=0, offset=0, length=4, stream_data=num_streams.to_bytes(4, 'big'), flags=StreamFrame.FIN_DATA_FRAME)]
        )
        self.packet_number += 1
        self.socket.sendto(request_packet.serialize(), self.address)
        print(f"Requested {num_streams} streams/files from the server.")


    def handle_stream_request(self, packet: QUICPacket):
        """Server handles the client's stream/file request."""
        
        stream_frame = packet.frames[0]
        num_streams = int.from_bytes(stream_frame.stream_data, 'big')
        print(f"Received request for {num_streams} streams/files from the client.")
           
        self.events.put(StreamRequestEvent(num_streams))


    def send_stream_data(self, stream_id: int, data: bytes, end_of_stream: bool):
        """Creates a StreamFrame and adds it to the queue of streamframes to send."""
        # If the stream does not exist yet, create it
        if stream_id not in self.streams:
            self.streams[stream_id] = QUICStream(stream_id)

        # Access the stream sender through the stream
        stream = self.streams[stream_id]
        stream_frame = stream.sender.send_data(data, end_of_stream)

        self.stream_frame_queue.put(stream_frame)

        if end_of_stream:
            print(f"Stream {stream_id} has finished sending.")
            stream.close()
            self.fin_streams.add(stream_id)



    def send_datagram(self):
        """Send all frames in the queue."""
        frames = []
        while not self.stream_frame_queue.empty():
            frames.append(self.stream_frame_queue.get())

        if frames:
            # Increment the packet number for each packet sent
            self.packet_number += 1
            packet = QUICPacket(
                flags=self.STREAM_DATA_FLAG, 
                connection_id=self.connection_id, 
                packet_number=self.packet_number, 
                frames=frames
            )
            try:
                self.socket.sendto(packet.serialize(), self.address)
                self.packets_to_ack[self.packet_number] = packet
            except socket.error as e:
                print(f"Socket error: {e}")



    def send_ack(self, packet_number: int):
        """Send an acknowledgment packet for the received packet."""
        ack_packet = QUICPacket(
            flags=self.ACK_FLAG,
            connection_id=self.connection_id,
            packet_number=packet_number,
            frames=[]
        )
        self.socket.sendto(ack_packet.serialize(), self.address)


    def send(self, stream_id: int, data: bytes, end_of_stream: bool):
        """Encapsulates send_stream_data and send_datagram."""
        # Check if the stream is closed
        if stream_id in self.fin_streams:
            print(f"Cannot send data: Stream {stream_id} is already closed.")
            return

        self.send_stream_data(stream_id, data, end_of_stream)

        # Calculate 60% of not closed streams
        not_closed_streams = len(self.streams) - len(self.fin_streams)
        threshold = 0.6 * not_closed_streams

        # If the number of frames is 60% of the number of not closed streams, send the datagram
        if self.stream_frame_queue.qsize() >= threshold:
            self.send_datagram()
            
            # Wait for ack on the packet
            self.recv()



    def recv_stream_data(self, frame: StreamFrame):
        """Process the received stream data and handle end-of-stream."""
        # If the stream does not exist yet, create it
        if frame.stream_id not in self.streams:
            self.streams[frame.stream_id] = QUICStream(frame.stream_id)

        stream = self.streams[frame.stream_id]
        event = stream.receiver.receive_stream_frame(frame)
        self.events.put(event)

        if event.end_of_stream:
            print(f"Stream {event.stream_id} has received the end of data.")
            stream.close()
            self.fin_streams.add(event.stream_id)




    def recv_datagram(self):
        """Receive a datagram and deserialize it."""
        try:
            data, addr = self.socket.recvfrom(65535)  # Buffer size of 65535 bytes

            if addr != self.address:
                print(f"Received data from unexpected address {addr}.")
                return None

            # Deserialize the packet
            packet = QUICPacket.deserialize(data)
            if packet.connection_id != self.connection_id:
                print(f"Received packet with mismatched connection ID: {packet.connection_id}")
                return None

            return packet

        except socket.error as e:
            print(f"Socket error: {e}")
            return None
        except Exception as e:
            print(f"Error in recv_datagram: {e}")
            return None
        


    def recv(self):
        """Encapsulates recv_datagram and recv_stream_data."""
        packet = self.recv_datagram()
        if packet is None:
            return

        elif packet.flags & self.FIN_FLAG:
            self.recv_fin()
            return

        elif packet.flags & self.STREAM_REQUEST_FLAG:
            self.handle_stream_request(packet)
            return

        elif packet.packet_number in self.packets_to_ack:
            print(f"Recived ack for packet {packet.packet_number}")
            self.packets_to_ack.pop(packet.packet_number)
            return

        for frame in packet.frames:
            if isinstance(frame, StreamFrame):
                if frame.stream_id not in self.fin_streams:
                    self.recv_stream_data(frame)
                else:
                    print(f"Cannot recieve data: Stream {frame.stream_id} is already closed.")
        self.send_ack(packet.packet_number)
                


    def close(self):
        """Sends a FIN packet to close the stream or connection."""
        fin_packet = QUICPacket(
            flags=self.FIN_FLAG,
            connection_id=self.connection_id,
            packet_number=self.packet_number,
            frames=[]  # No stream frames needed for FIN
        )
        self.packet_number += 1
        self.socket.sendto(fin_packet.serialize(), self.address)

        print("Sent FIN packet")

        packet = self.recv_datagram()

        if packet.flags & self.FIN_ACK_FLAG:
            # Send ACK to confirm receipt of FIN_ACK
            ack_packet = QUICPacket(
                flags=self.ACK_FLAG,
                connection_id=self.connection_id,
                packet_number=self.packet_number,
                frames=[]
            )
            self.packet_number += 1
            self.socket.sendto(ack_packet.serialize(), self.address)
            print(f"Sent ACK for FIN_ACK. Connection closed.")


    def recv_fin(self):
        """Handles a FIN packet and sends a FIN_ACK."""
        print(f"Received FIN for connection {self.connection_id}.")
    
        # Send FIN_ACK to acknowledge the FIN
        fin_ack_packet = QUICPacket(
            flags=self.FIN_ACK_FLAG,
            connection_id=self.connection_id,
            packet_number=self.packet_number,
            frames=[]
        )
        self.packet_number += 1
        self.socket.sendto(fin_ack_packet.serialize(), self.address)

        print(f"Sent FIN_ACK for connection {self.connection_id}.")

        ack_packet = self.recv_datagram()
        if ack_packet.flags & self.ACK_FLAG:
            print("Received acknowledgment for FIN_ACK. Connection closed successfully.")
