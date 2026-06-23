# ====================================================================================================
# @file: network.py

# Handles connecting to the server, sending messages, and receiving responses.

# ====================================================================================================
import socket
import sys
import threading
import time
# add parent directory so we can import from shared/protocol.py
sys.path.append('..')
from shared.protocol import (
    send_message, receive_message, MESSAGE_NAMES,
    MESSAGE_WELCOME, MESSAGE_USERNAME, MESSAGE_USERNAME_ACK,
    MESSAGE_CHAT, MESSAGE_REPLY, MESSAGE_EVENT,
    MESSAGE_QUIT, MESSAGE_ERROR,
    MESSAGE_GIFT, MESSAGE_DONATE, MESSAGE_SUBSCRIBE, MESSAGE_LIKE
)

class HarpyStreamClient:
    # ====================================================================================================
        # @brief: Initialize the client with a host and port. The default is localhost:3012.
        # @attr host: The IP address or hostname of the server to connect to (default 'localhost')
        # @attr port: The TCP port number of the server to connect to 
        # @attr client_socket: The TCP socket object that will be used to communicate with the server
    # ====================================================================================================
    def __init__(self, host: str = 'localhost', port: int = 3012):
        self.host = host
        self.port = port
        self.client_socket = None
        self.username = None

    # ====================================================================================================
        # @brief: Connect to the server by creating a socket and connecting to the specified host and port.
    # ====================================================================================================
    def connect_to_server(self):
        try:
            # Create the socket and connect to the server. starts the TCP three-way handshake 
            # Three way handshake:
                # 1. Client → Server:  SYN        (I want to connect)
                # 2. Server → Client:  SYN-ACK    (Acknowledged, I'm ready too)
                # 3. Client → Server:  ACK        (Great, let's go)
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"[CLIENT] Connecting to the stream at {self.host}:{self.port}...")
            self.client_socket.connect((self.host, self.port))
            print(f"[CLIENT] Successfully Joined!")
       
            # Wait for welcome message (asks for username)
            message_type, payload = receive_message(self.client_socket)
            if message_type == MESSAGE_WELCOME:
                stream_title = payload.get("stream_title", "")
                if stream_title:
                    print(f"  {stream_title}\n")
                print(payload.get("message", ""))
 
            # grab viewer's (client) username
            self.username = input("\nEnter your username: ").strip()
            if not self.username:
                self.username = "anonymous"

            send_message(self.client_socket, MESSAGE_USERNAME, {
                "username": self.username
            })
 
            # wait for harpy's reply
            message_type, payload = receive_message(self.client_socket)
            if message_type == MESSAGE_USERNAME_ACK:
                sender = payload.get("sender", "Harpy")
                print(f"\n  {sender}: {payload.get('message', '')}\n")

            self.print_help()

            receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            receive_thread.start()

            self.main_chat_loop()
    
        # case where the server isn't running, connect() raises ConnectionRefusedError
        except ConnectionRefusedError:
            print(f"[CLIENT] Could not connect. Is the stream running?")
        except Exception as e:
            print(f"[CLIENT] Error connecting to stream: {e}")
        finally:
            self.disconnect()

    
    # ====================================================================================================
    # @brief: print available commands for the viewer.
    # ====================================================================================================
    def print_help(self):
        print("=" * 50)
        print("  Commands:")
        print("  /gift <amount>        — Send a gift")
        print("  /donate <amount> <msg> — Donate with a message")
        print("  /subscribe            — Subscribe to the stream")
        print("  /like                 — Like the stream")
        print("  /help                 — Show help")
        print("  /quit                 — Leave the stream")
        print("  (anything else)       — Send a chat message")
        print("=" * 50)
        print()

    # ====================================================================================================
    # @brief: Continuously receive messages from the server in a background thread.
    #         Handles ALL incoming data: welcome message, chat responses, broadcast events.
    # ====================================================================================================
    def receive_loop(self):
            try:
                while True:
                    message_type, payload = receive_message(self.client_socket)

                    if message_type is None:
                        print("\n[CLIENT] Stream ended.")
                        break

                    message_content = payload.get("message", "")

                    if message_type == MESSAGE_REPLY:
                        print(f"\n  {message_content}")

                    elif message_type == MESSAGE_USERNAME_ACK:
                        sender = payload.get("sender", "Harpy")
                        print(f"\n  {sender}: {message_content}")

                    elif message_type == MESSAGE_EVENT:
                        print(f"\n  {message_content}")

                    elif message_type == MESSAGE_ERROR:
                        print(f"\n  [ERROR] {message_content}")

                    else:
                        readable_type = MESSAGE_NAMES.get(message_type, "UNKNOWN")
                        print(f"\n  [{readable_type}] {message_content}")

                    # reprint prompt
                    print(f"  {self.username}: ", end="", flush=True)

            except ConnectionResetError:
                print("\n[CLIENT] Lost connection to stream.")
            except OSError:
                pass

    # ====================================================================================================
    #   @brief: the main interaction loop with the server. It will send a message to the server and wait for 
    #           a response

    # ====================================================================================================
    def main_chat_loop(self):
        try:
            while True:
                # input from user
                message = input().strip()
                # skip empty messages
                if not message:
                    continue
                # parse incoming command
                if message.startswith("/"):
                    message_parts = message.split(maxsplit=2)
                    command = message_parts[0].lower()
                    # after parsed, check which category does the command falls to
                    if command == "/quit":
                        send_message(self.client_socket, MESSAGE_QUIT, {
                            "message": "quit"
                        }) 
                        time.sleep(0.5)
                        break

                    elif command == "/gift":
                        gift_amount = int(message_parts[1]) if len(message_parts) > 1 and message_parts[1].isdigit() else 1000
                        send_message(self.client_socket, MESSAGE_GIFT, {
                            "amount": gift_amount
                        })

                    elif command == "/donate":
                        donate_amount = int(message_parts[1]) if len(message_parts) > 1 and message_parts[1].isdigit() else 5000
                        donate_message = message_parts[2] if len(message_parts) > 2 else "Keep up the great stream :D!"
                        send_message(self.client_socket, MESSAGE_DONATE, {
                            "amount": donate_amount,
                            "message": donate_message
                        })
                    
                    elif command == "/subscribe":
                        send_message(self.client_socket, MESSAGE_SUBSCRIBE, {})
                    
                    elif command == "/like":
                        send_message(self.client_socket, MESSAGE_LIKE, {})

                    elif command == "/help":
                        self.print_help()

                    else:
                        print(f" Uh oh, command unknown: {command}. Type /help for commands!")
                # just a regular message. send it anyways
                else:
                    send_message(self.client_socket, MESSAGE_CHAT, {
                        "message": message
                    })

        # exit gracefully on Ctrl+C (SIGINT)
        except KeyboardInterrupt:
            print("\n[CLIENT] Leaving the stream...")

    # ====================================================================================================
    # @brief: Close the client socket to disconnect from the server.
    # ====================================================================================================
    def disconnect(self):
        if self.client_socket:
            self.client_socket.close()
            print("[CLIENT] Leaving the Stream. Thanks for joining ^w^ \n")
    # Note:
    # close() sends a FIN packet to the server, signaling that we're done.The server's recv() will then 
    # return b"", which it detects as a disconnect.


    
# NOT NEEDED

    # # ====================================================================================================
    # # @brief: Send a message to the server by encoding it to bytes and using the socket's send() method.
    # # @param:
    # #     message: The string message to send to the server.
    # # ====================================================================================================
    # def send_message(self, message: str):
    #     # use sendall() to ensure the entire message is sent 
    #     # (even though size is not an issue for short chat messages)
    #     self.client_socket.sendall(encode(message))

    # # ====================================================================================================
    # # @brief: Receive a message from the server by using the socket's recv() method and decoding 
    # #         the bytes to a string.
    # # @return: The received message as a string, or None if the connection is closed.
    # # ====================================================================================================
    # def receive_message(self) -> str | None:
    #     data = self.client_socket.recv(BUFFER_SIZE)
    #     # if recv() returns empty bytes, the connection is closed
    #     if not data:
    #         return None
    #     return decode(data)
    
