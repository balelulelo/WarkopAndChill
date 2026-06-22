# ====================================================================================================
    # @file: server.py (Phase 3)
    
    # WHAT CHANGED FROM PHASE 2:
    # - All send/recv now use send_message() and receive_message() from protocol.py
    # - Messages have types (MESSAGE_TYPE_WELCOME, MESSAGE_TYPE_REPLY, etc.)
    # - Payloads are dicts, not raw strings
    # - receive_message() handles framing — no more message-merging bugs
    
    # WHAT STAYED THE SAME:
    # - Threading model (one thread per client)
    # - Socket setup (socket, bind, listen, accept)
    # - connected_clients tracking with Lock
# ====================================================================================================
import socket
import sys
import threading

sys.path.append('..')  
from shared.protocol import (
    send_message, receive_message, MESSAGE_TYPE_NAMES,
    MESSAGE_TYPE_WELCOME, MESSAGE_TYPE_SELECT, MESSAGE_TYPE_SELECT_ACK,
    MESSAGE_TYPE_CHAT, MESSAGE_TYPE_REPLY, MESSAGE_TYPE_EVENT, 
    MESSAGE_TYPE_QUIT, MESSAGE_TYPE_ERROR
)


class WarkopServer:
    # ====================================================================================================
    # @brief: Initialize the server.
    # @attr host: IP address to bind to (default 'localhost')
    # @attr port: TCP port to listen on (default 3012)
    # @attr server_socket: The main listening socket
    # @attr connected_clients: Dict of {client_socket: address} for all active connections
    # @attr client_lock: Threading lock protecting connected_clients
    # ====================================================================================================
    def __init__(self, host: str = 'localhost', port: int = 3012):
        self.host = host
        self.port = port
        self.server_socket = None
        self.connected_clients = {}  
        self.client_lock = threading.Lock() 

    # ====================================================================================================
    # @brief: Start the server. Socket setup identical to Phase 1 and 2.
    # ====================================================================================================
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1)  

        print(f"[SERVER] Welcome, Our Warkop is Open Now!\n")
        print(f"[SERVER] Listening on {self.host}:{self.port}...\n")
        print(f"[SERVER] Waiting for our dear customer...")

        self.accept_connections()

    # ====================================================================================================
    # @brief: Accept connections and spawn a thread per client.
    # ====================================================================================================
    def accept_connections(self):
        try:
            while True:
                try:
                    client_socket, client_address = self.server_socket.accept()
                except socket.timeout:  
                    continue  
                except KeyboardInterrupt:
                    raise
                print(f"\n[SERVER] We got a Customer from {client_address[0]}:{client_address[1]}!\n")

                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_address),
                    daemon=True  
                )
                client_thread.start()

                with self.client_lock:
                    active_clients = len(self.connected_clients)
                print(f"[SERVER] Currently serving {active_clients} customer(s)...\n")

        except KeyboardInterrupt:
            print("\n[SERVER] Closing the Warkop. See you next time!")
        finally:
            self.server_socket.close()

    # ====================================================================================================
    # @brief: Handle one client connection using the binary protocol.
    #
    # KEY CHANGES FROM PHASE 2:
    #   BEFORE: client_socket.send(encode("Welcome!"))
    #   AFTER:  send_message(client_socket, MESSAGE_TYPE_WELCOME, {"message": "Welcome!"})
    #
    #   BEFORE: data = client_socket.recv(BUFFER_SIZE); message = decode(data)
    #   AFTER:  message_type, payload = receive_message(client_socket)
    # ====================================================================================================
    def handle_client(self, client_socket: socket.socket, client_address: tuple):
        with self.client_lock:
            self.connected_clients[client_socket] = client_address
            current_client_count = len(self.connected_clients)
        
        try:
            # Send welcome using the protocol
            send_message(client_socket, MESSAGE_TYPE_WELCOME, {
                "message": (
                    f"Welcome to our Warkop! You are customer number {current_client_count}.\n"
                    f"What can we help you with today?\n"
                    f"Type 'quit' to leave the warkop."
                )
            })

            # Broadcast to others that a new customer arrived
            self.broadcast_event(
                f"A new customer just walked in! We now have {current_client_count} customers in the warkop.",
                exclude=client_socket
            )

            while True:
                # Receive a framed message — returns (type, dict) or (None, None)
                message_type, payload = receive_message(client_socket)

                # (None, None) means connection closed cleanly
                if message_type is None:
                    print(f"[SERVER] Customer {client_address[0]}:{client_address[1]} has left.")
                    break
                
                # Log with human-readable type name
                readable_type = MESSAGE_TYPE_NAMES.get(message_type, f"UNKNOWN({message_type})")
                print(f"[SERVER] [{readable_type}] from {client_address[0]}:{client_address[1]}: {payload}\n")

                # Handle based on message type
                if message_type == MESSAGE_TYPE_QUIT:
                    send_message(client_socket, MESSAGE_TYPE_REPLY, {
                        "message": "Thank you for visiting! See you next time!"
                    })
                    print(f"[SERVER] Customer {client_address[0]}:{client_address[1]} said goodbye.\n")
                    break
                
                elif message_type == MESSAGE_TYPE_CHAT:
                    # Phase 4 will route this to the character engine
                    # For now, echo it back as a REPLY
                    user_message = payload.get("message", "")
                    send_message(client_socket, MESSAGE_TYPE_REPLY, {
                        "message": f"You said: {user_message}"
                    })
                
                elif message_type == MESSAGE_TYPE_SELECT:
                    # Phase 4 will handle character selection
                    selected_character = payload.get("character", "unknown")
                    send_message(client_socket, MESSAGE_TYPE_SELECT_ACK, {
                        "message": f"You selected {selected_character}. (Character engine coming in Phase 4!)"
                    })
                
                else:
                    send_message(client_socket, MESSAGE_TYPE_ERROR, {
                        "message": f"Unknown message type: {readable_type}"
                    })

        except ConnectionResetError:
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} was reset.\n")
        except Exception as error:
            print(f"[SERVER] Error with {client_address[0]}:{client_address[1]}: {error}\n")
        finally:
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
    # @brief: Broadcast an event to all connected clients using MESSAGE_TYPE_EVENT.
    # @param:
    #   message: The event text to broadcast
    #   exclude: Optional socket to skip (e.g., don't notify the person who triggered the event)
    # ====================================================================================================
    def broadcast_event(self, message: str, exclude: socket.socket = None):
        with self.client_lock:
            clients_snapshot = dict(self.connected_clients) 

        for client_socket in clients_snapshot:
            if client_socket is not exclude:
                try:
                    send_message(client_socket, MESSAGE_TYPE_EVENT, {"message": message})
                except Exception:
                    pass