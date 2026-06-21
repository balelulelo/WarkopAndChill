"""
@file: protocol.py

Simple UTF-8 string encoding. convert strings to bytes for sending,
and converts bytes back to strings for reading. 

"""

BUFFER_SIZE = 1024
ENCODING = 'utf-8'


"""
@brief: Convert a string message into bytes for sending over TCP.
TCP sockets only transmit raw bytes, not Python strings.T
 
@param:
    message: The text to send (e.g., "hello" or "pick a character")
 
@return:
    the message as a UTF-8 byte sequence (e.g., b"hello")
"""
def encode(message: str) -> bytes:
    return message.encode(ENCODING)

"""
@brief: Convert received bytes back into a string. When recv() 
        returns data from the socket, it's raw bytes.
 
@param:
    data: Raw bytes from socket.recv() (e.g., b"hello")
 
@return:
    The decoded string (e.g., "hello")
"""
def decode(data: bytes) -> str:
    return data.decode(ENCODING)