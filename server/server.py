# ====================================================================================================
    # @file: server.py
# ====================================================================================================
import socket
import sys
import threading
# add parent directory so we can import from shared/protocol.py
sys.path.append('..')  
from shared.protocol import encode, decode, BUFFER_SIZE

# ================================================================================
# @brief: A TCP server that listens for client connections.
# ================================================================================
class WarkopServer:
    # ====================================================================================================
    # @brief: Initialize the server with a host and port. The default is localhost:3012.
    # @attr host: The IP address or hostname to bind to (default 'localhost')
    # @attr port: The TCP port number to listen on 
    # @attr server_socket: The TCP socket object that will listen for connections
    # @attr connected_clients: A dictionary to keep track of connected clients (currently not used)
    # @attr client_lock: A threading lock to protect access to the connected_clients 
    #                    dictionary (currently not used)
    # ====================================================================================================
    def __init__(self, host: str = 'localhost', port: int = 3012):
        self.host = host
        self.port = port
        self.server_socket = None
        self.connected_clients = {}  
        self.client_lock = threading.Lock() 

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
                    # just loop back and wait for the next connection
                    continue  
                except KeyboardInterrupt:
                    # raise KeyboardInterrupt to break out of the outer loop and exit gracefully
                    raise
                print(f"\n[SERVER] We got a Customer from {client_address[0]}:{client_address[1]}!\n")

                # spawn a new thread to handle this client, so that the main thread can go back to 
                # accepting new clients
                
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_address),
                    # make the thread a daemon so it exits when the main thread exits
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
            welcome_message = (
                f"Welcome to our Warkop! You are customer number {current_clients}.\n"
                f"What can we help you with today?\n"
                f"Type 'quit' to leave the warkop.\n"
            )
            client_socket.send(encode(welcome_message))
            # notify others a new client has joined
            self.broadcast_event(
                f"[Warkop] A new customer just walked in! We now have {current_clients} customers in the warkop.",
                exclude=client_socket
            )
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    # no data means the client closed the connection
                    print(f"[SERVER] Customer from {client_address[0]}:{client_address[1]} has left.")
                    break
                # decode raw bytes to string
                message = decode(data).strip()
                print(f"[SERVER] Received from {client_address[0]}:{client_address[1]}: {message}\n")

                # break the loop and close connection if client types 'quit'
                if message.lower() == 'quit':
                    goodbye_message = "Thank you for visiting! See you next time!\n"
                    client_socket.send(encode(goodbye_message))
                    print(f"[SERVER] Customer from {client_address[0]}:{client_address[1]} has left.\n")
                    break
                # print back the message to client
                response = f"You said: {message}\n"
                client_socket.send(encode(response))

        except ConnectionResetError:
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} was reset.\n")
    
        except Exception as e:
            print(f"[SERVER] An error with address {client_address[0]}:{client_address[1]} occurred: {e}\n")

        # always close client socket when done, whether normal exit or error
        finally:
            # remove this client from the connected_clients dictionary
            with self.client_lock:
                if client_socket in self.connected_clients:
                    del self.connected_clients[client_socket]
                remaining = len(self.connected_clients)

            client_socket.close()
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} closed.\n")
            self.broadcast_event(
                f"[Warkop] A customer just left. We now have {remaining} customers in the warkop."
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
                    client_socket.send(encode(message + "\n"))
                except Exception as e:
                    pass