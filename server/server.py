# ====================================================================================================
    # @file: server.py
# ====================================================================================================
import socket
import sys
import threading
import os
# add parent directory so we can import from shared/protocol.py
sys.path.append('..')  
from shared.protocol import(
    send_message, receive_message, MESSAGE_NAMES, MESSAGE_WELCOME,
    MESSAGE_SELECT, MESSAGE_SELECT_ACK, MESSAGE_CHAT, MESSAGE_REPLY,
    MESSAGE_EVENT, MESSAGE_QUIT, MESSAGE_ERROR,
    MESSAGE_GIFT, MESSAGE_DONATE, MESSAGE_SUBSCRIBE, MESSAGE_LIKE
)
from session import ViewerSession
from character_engine import CharacterEngine
from broadcast_engine import BroadcastEngine

# ================================================================================
# @brief: A TCP server that listens for client connections.
# ================================================================================
class HarpyStreamServer:
    # ====================================================================================================
    # @brief: TCP server for harpy's live stream.
    # @attr host: IP address to bind to
    # @attr port: TCP port to listen on
    # @attr server_socket: The main listening socket
    # @attr connected_clients: Dict of {client_socket: ViewerSession}
    # @attr client_lock: Threading lock protecting connected_clients
    # @attr harpy: The character engine (harpy's brain)
    # @attr broadcaster: The broadcast engine (harpy's auto-commentary)
    # ====================================================================================================
    def __init__(self, host: str = 'localhost', port: int = 3012):
        self.host = host
        self.port = port
        self.server_socket = None
        self.connected_clients = {}  
        self.client_lock = threading.Lock() 
        # Load harpy's character from config
        config_path = os.path.join(os.path.dirname(__file__), 'characters', 'harpy.json')
        self.harpy = CharacterEngine(config_path)
 
        # Broadcast engine — pass our broadcast_event method as the callback
        self.broadcaster = BroadcastEngine(self.harpy, self.broadcast_event)

    # ====================================================================================================
    # @brief: Start the server by creating a socket, binding it, and listening for connections.
    # ====================================================================================================
    
    def start_server(self):
        # set socket TCP and IPv4, set reusable address, bind to address, 
        # and start listening
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        # timeout to allow graceful chutdown
        self.server_socket.settimeout(1)  

        # some print messages to show that server is running:
        print(f"[SERVER] Welcome, Our Warkop is Open Now!\n")
        print(f"[SERVER] Listening on {self.host}:{self.port}...\n")
        print(f"[SERVER] Waiting for our dear customer...")

        self.accept_connections()

    # ====================================================================================================
    # @brief: Accept incoming client connections in a loop. For each accepted connection, 
    #         call handle_client() to interact with that client.
    # ====================================================================================================

    def accept_connections(self):
        try:
            while True:
                try:
                # block until a client connects to server, and handles this client
                # while blocking so no other client enters before this one leaves
                    client_socket, client_address = self.server_socket.accept()
                except socket.timeout:  
                    continue  
                except KeyboardInterrupt:
                    raise
                print(f"\n[SERVER] We got a Customer from {client_address[0]}:{client_address[1]}!\n")

                # spawn a new thread to handle this client, so that the main thread can go back to 
                # accepting new clients
                
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_address),
                    daemon=True  
                )
                client_thread.start()

                # count how much current active customers (not really important actually, but why not)
                with self.client_lock:
                    active_clients = len(self.connected_clients)
                print(f"[SERVER] Currently serving {active_clients} customer(s)...\n")
        # when receiving interrupt signal (CTRL + C), exit gracefully
        except KeyboardInterrupt:
            print("\n[SERVER] Closing the Warkop. See you next time!")
        finally:
            self.server_socket.close()

    # ====================================================================================================
    # @brief: Handle communication with a single client. This method is called after a client connects.
    # @param:
        # client_socket: The socket object that represents the connection to this client. 
        # client_address: A tuple (ip, port) that identifies the client's address.
    # ====================================================================================================

    def handle_client(self, client_socket: socket.socket, client_address: tuple):
        # add this client to the connected_clients dictionary 
        with self.client_lock:
            self.connected_clients[client_socket] = client_address
            current_clients = len(self.connected_clients)
        
        try:
            send_message(client_socket, MESSAGE_WELCOME, {
                "message": (
                    f"Welcome to our Warkop! You are customer number {current_clients}.\n"
                    f"What can we help you with today?\n"
                    f"Type 'quit' to leave the warkop.\n"
                )
            })
            # notify others a new client has joined
            self.broadcast_event(
                f"[Warkop] A new customer just walked in! We now have {current_clients} customers in the warkop.",
                exclude=client_socket
            )
            while True:
                # Receive a framed message — returns (type, dict) or (None, None)
                message_type, payload = receive_message(client_socket)

                if message_type is None:
                    print(f"[SERVER] Customer {client_address[0]}:{client_address[1]} has left.")
                    break

                # human readable log
                readable_type = MESSAGE_NAMES.get(message_type, f"UNKNOWN({message_type})")
                print(f"[SERVER] [{readable_type}] from {client_address[0]}:{client_address[1]}: {payload}\n")

                # 1. if message type is quit
                if message_type == MESSAGE_QUIT:
                    send_message(client_socket, MESSAGE_REPLY, {
                        "message": "Thank you for visiting! See you next time!"
                    })
                    print(f"[SERVER] Customer {client_address[0]}:{client_address[1]} said goodbye.\n")
                    break
                # 2. if message type is chat
                elif message_type == MESSAGE_CHAT:
                    # i'll route this to the actual characters later. placeholder
                    user_message = payload.get("message", "")
                    send_message(client_socket, MESSAGE_REPLY, {
                        "message": f"You said: {user_message}"
                    })
                # 3. if message type is select
                elif message_type == MESSAGE_SELECT:
                    # Phase 4 will handle character selection
                    selected_character = payload.get("character", "unknown")
                    send_message(client_socket, MESSAGE_SELECT_ACK, {
                        "message": f"You selected {selected_character}. (Character engine coming in Phase 4!)"
                    })
                # 4. other than that, it's unknown
                else:
                    send_message(client_socket, MESSAGE_ERROR, {
                        "message": f"Unknown message type: {readable_type}"
                    })

        except ConnectionResetError:
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} was reset.\n")
    
        except Exception as e:
            print(f"[SERVER] An error with address {client_address[0]}:{client_address[1]} occurred: {e}\n")

        # always close client socket when done, whether normal exit or error
        finally:
            # remove this client from the dictionary
            with self.client_lock:
                if client_socket in self.connected_clients:
                    del self.connected_clients[client_socket]
                remaining_clients = len(self.connected_clients)

            client_socket.close()
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} closed.\n")

            self.broadcast_event(
                f"A customer just left. We now have {remaining_clients} customers in the warkop."
            )
    
    # ====================================================================================================
    # @brief: Broadcast a message to all connected clients, optionally excluding one client.
    # @param:
        # message: The string message to broadcast to all clients.
        # exclude: An optional socket object to exclude from the broadcast (e.g., the sender).  
    # ====================================================================================================
    def broadcast_event(self, message: str, exclude: socket.socket = None):
        # iterate over a copy of the connected_clients dictionary to avoid issues if clients disconnect 
        # while broadcasting
        with self.client_lock:
            clients_copy = dict(self.connected_clients) 

        for client_socket in clients_copy:
            if client_socket != exclude:
                try:
                    send_message(client_socket, MESSAGE_EVENT, {"message": message})
                except Exception as e:
                    pass