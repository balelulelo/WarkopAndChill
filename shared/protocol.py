# ====================================================================================================

# @file: protocol.py

# Simple UTF-8 string encoding. convert strings to bytes for sending,
# and converts bytes back to strings for reading. 
# Added custom binary protocol

# ====================================================================================================
import json
import struct
import socket

BUFFER_SIZE = 1024
ENCODING = 'utf-8'
# total header size with this will be 3 bytes
HEADER_FORMAT = '!HB' 
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# message types in a single byte (hex) 
MESSAGE_WELCOME = 0x01
MESSAGE_SELECT = 0x02
MESSAGE_SELECT_ACK = 0x03
MESSAGE_CHAT = 0x04
MESSAGE_REPLY = 0x05
MESSAGE_EVENT = 0x06
MESSAGE_QUIT = 0x07
MESSAGE_ERROR = 0x08

MESSAGE_TYPE_NAMES = {
    MESSAGE_WELCOME:  "WELCOME",
    MESSAGE_SELECT: "SELECT",
    MESSAGE_SELECT_ACK: "SELECT_ACK",
    MESSAGE_CHAT:   "CHAT",
    MESSAGE_REPLY:  "REPLY",
    MESSAGE_EVENT:  "EVENT",
    MESSAGE_QUIT:   "QUIT",
    MESSAGE_ERROR:  "ERROR",
}

# ====================================================================================================
#   @brief: Pack a message into binary wire format and send it over a socket.
#
#   @param:
#       sock:     The socket to send through
#       msg_type: One of the MSG_* constants (e.g., MSG_CHAT, MSG_EVENT)
#       payload:  A dictionary that will be JSON-serialized
# ====================================================================================================

def send_message(target_socket: socket.socket, message_type: int, payload: dict):
    payload_bytes = json.dumps(payload).encode(ENCODING)
    header = struct.pack(HEADER_FORMAT, len(payload_bytes), message_type)
    sock.sendall(header + payload_bytes) 

# ====================================================================================================
# @brief: Receive exactly `num_bytes` bytes from a socket.
#
# @param:
#   source_socket:  The socket to receive from
#   num_bytes:      Exact number of bytes to read
#
# @return:
#   Exactly num_bytes bytes, or None if the connection closed before completing
# ====================================================================================================

def receive_exact(socket: socket.socket, num_bytes: int) -> bytes | None:
    data_accumulated = b''
    while len(data_accumulated) < num_bytes:
        remaining_bytes = num_bytes - len(accumulated_data)
        chunk = source_socket.recv(remaining_bytes)
        if not chunk:
            return None
        accumulated_data += chunk
    return accumulated_data

# ====================================================================================================
# @brief: Receive one complete message from a socket.
#
# @param:
#   source_socket: The socket to receive from
#
# @return:
#   Tuple of (message_type: int, payload: dict), or (None, None) if disconnected
# ====================================================================================================
def receive_message(source_socket: socket.socket) -> tuple:
    header_data = receive_exact(source_socket, HEADER_SIZE)
    if header_data is None:
        return None, None
    
    payload_length, message_type = struct.unpack(HEADER_FORMAT, header_data) 

    payload_data = receive_exact(source_socket, payload_length)
    if payload_data is None:
        retrun None, None

    payload = json.loads(payload_data.decode(ENCODING))
    return message_type, payload

# ====================================================================================================

    # @brief: Convert a string message into bytes for sending over TCP.
    #         TCP sockets only transmit raw bytes, not Python strings.T
    
    # @param:
    #     message: The text to send (e.g., "hello" or "pick a character")
    
    # @return:
    #     the message as a UTF-8 byte sequence (e.g., b"hello")
# ====================================================================================================

def encode(message: str) -> bytes:
    return message.encode(ENCODING)

# ====================================================================================================

#   @brief: Convert received bytes back into a string. When recv() 
#           returns data from the socket, it's raw bytes.
    
#   @param:
#       data: Raw bytes from socket.recv() (e.g., b"hello")
    
#   @return:
#       The decoded string (e.g., "hello")
# ====================================================================================================

def decode(data: bytes) -> str:
    return data.decode(ENCODING)