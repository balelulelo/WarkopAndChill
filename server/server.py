"""
    @file: server.py
    
    This is the heart of the networking layer. Here's what it does:
    
    1. Creates a TCP socket
    2. Binds it to a host and port (claims that address)
    3. Listens for incoming connections
    4. Accepts a client connection (blocks until someone connects)
    5. Enters a loop: receive a message, echo it back
    6. Cleans up when the client disconnects

"""
import socket
import sys
# add parent directory so we can import from shared/protocol.py
sys.path.append('..')  
from shared.protocol import encode, decode, BUFFER_SIZE

"""
@brief: A TCP server that listens for client connections.
"""
class WarkopServer:
    """
        @brief: Initialize the server with a host and port. The default is localhost:3012.
        @attr host: The IP address or hostname to bind to (default 'localhost')
        @attr port: The TCP port number to listen on 
        @attr server_socket: The TCP socket object that will listen for connections
    """
    def __init__(self, host: str = 'localhost', port: int = 3012):
        self.host = host
        self.port = port
        self.server_socket = None

    """
        @brief: Start the server by creating a socket, binding it, and listening for connections.

    """
    def start_server(self):
        # set socket TCP and IPv4, set reusable address, bind to address, 
        # and start listening
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen() 

        # some print messages to show that server is running:
        print(f"[SERVER] Welcome, Our Warkop is Open Now!\n")
        print(f"[SERVER] Listening on {self.host}:{self.port}...\n")
        print(f"[SERVER] Waiting for our dear customer...")

        self.accept_connections()

    """
        @brief: Accept incoming client connections in a loop. For each accepted connection, 
                call handle_client() to interact with that client.

    """
    def accept_connections(self):
        try:
            while True:
                # block until a client connects to server, and handles this client
                # while blocking so no other client enters before this one leaves
                client_socket, client_address = self.server_socket.accept()
                print(f"[SERVER] Ah! We got a customer from {client_address}.\n")
                self.handle_client(client_socket, client_address)
        except KeyboardInterrupt:
            # when receiving interrupt signal (CTRL + C), exit gracefully
            print("\n[SERVER] Closing the Warkop. See you next time!")
        finally:
            self.server_socket.close()

    """
        @brief: Handle communication with a single client. This method is called after a client connects.
        @param:
            client_socket: The socket object that represents the connection to this client. 
            client_address: A tuple (ip, port) that identifies the client's address.
    """
    def handle_client(self, client_socket: socket.socket, client_address: tuple):
        try:
            welcome_message = "Welcome to our Warkop! What can i help you with?\nType 'quit' to leave."
            client_socket.send(encode(welcome_message))

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
        # handle case where client crashed or forcefully closed their connection
        except ConnectionResetError:
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} was reset.\n")
    
        except Exception as e:
            print(f"[SERVER] An error with address {client_address[0]}:{client_address[1]} occurred: {e}\n")
        # always close client socket when done, whether normal exit or error
        finally:
            client_socket.close()
            print(f"[SERVER] Connection with {client_address[0]}:{client_address[1]} closed.\n")