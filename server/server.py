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
    MESSAGE_USERNAME, MESSAGE_USERNAME_ACK, MESSAGE_CHAT, MESSAGE_REPLY,
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
        print(f"[SERVER] {self.harpy.name}'s stream is starting!")
        print(f"[SERVER] Listening on {self.host}:{self.port}...")
        print(f"[SERVER] Harpy's mood: {self.harpy.current_mood}\n")
        self.broadcaster.start_broadcast()
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
                print(f"\n[SERVER] New Viewer from {client_address[0]}:{client_address[1]}!\n")

                # spawn a new thread to handle this client, so that the main thread can go back to 
                # accepting new clients
                
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_address),
                    daemon=True  
                )
                client_thread.start()
        # when receiving interrupt signal (CTRL + C), exit gracefully
        except KeyboardInterrupt:
            print(f"\n[SERVER] {self.harpy.name}'s stream is ending. Thanks for watching!")
        finally:
            self.broadcaster.stop_broadcast()
            self.server_socket.close()

    # ====================================================================================================
    # @brief: Handle communication with a single client. This method is called after a client connects.
    # @param:
        # client_socket: The socket object that represents the connection to this client. 
        # client_address: A tuple (ip, port) that identifies the client's address.
    # ====================================================================================================

    def handle_client(self, client_socket: socket.socket, client_address: tuple):
            viewer_session = ViewerSession()
            with self.client_lock:
                self.connected_clients[client_socket] = viewer_session
                current_clients = len(self.connected_clients)
            
            try:
                # 1: ask for username
                send_message(client_socket, MESSAGE_WELCOME, {
                    "message": f"Welcome to {self.harpy.name}'s stream! Please enter your username to join the chat.",
                    "stream_title": self.harpy.character_data.get("stream_title", "")
                })
    
                # 2: wait for username
                message_type, payload = receive_message(client_socket)
                if message_type is None:
                    return
    
                if message_type == MESSAGE_USERNAME:
                    viewer_session.username = payload.get("username", "anonymous")
                    send_message(client_socket, MESSAGE_USERNAME_ACK, {
                        "message": self.harpy.generate_welcome(viewer_session.username),
                        "username": viewer_session.username
                    })
                    with self.client_lock:
                        viewer_count = len(self.connected_clients)
                    self.broadcast_event(
                        f"{viewer_session.username} joined the stream! ({viewer_count} viewers)",
                        exclude=client_socket
                    )
                    print(f"[SERVER] Viewer '{viewer_session.username}' joined from {client_address[0]}:{client_address[1]}")
                else:
                    send_message(client_socket, MESSAGE_ERROR, {
                        "message": "Please set a username first!"
                    })
                    return
    
                # 3: main interaction loop
                while True:
                    message_type, payload = receive_message(client_socket)
    
                    if message_type is None:
                        print(f"[SERVER] Viewer '{viewer_session.username}' disconnected.")
                        break
    
                    readable_type = MESSAGE_NAMES.get(message_type, f"UNKNOWN({message_type})")
                    print(f"[SERVER] [{readable_type}] {viewer_session.username}: {payload}")
                    self.broadcaster.pause_briefly(3.0)
    
                    if message_type == MESSAGE_QUIT:
                        goodbye = self.harpy.generate_goodbye(viewer_session.username)
                        self.broadcast_event(f"{self.harpy.name}: {goodbye}")
                        break
    
                    elif message_type == MESSAGE_CHAT:
                        viewer_session.record_interaction()
                        user_message = payload.get("message", "")
                        response = self.harpy.respond_to_chat(viewer_session.username, user_message)
                        # broadcast viewer's message to everyone
                        self.broadcast_event(f"{viewer_session.username}: {user_message}")
                        # broadcast Harpy's reply to everyone
                        self.broadcast_event(f"{self.harpy.name}: {response}")
    
                    elif message_type == MESSAGE_GIFT:
                        amount = payload.get("amount", 0)
                        viewer_session.record_gift()
                        response = self.harpy.respond_to_gift(viewer_session.username, amount)
                        self.broadcast_event(f"🎁 {viewer_session.username} sent a gift worth {amount}!")
                        self.broadcast_event(f"{self.harpy.name}: {response}")
    
                    elif message_type == MESSAGE_DONATE:
                        amount = payload.get("amount", 0)
                        donate_message = payload.get("message", "")
                        viewer_session.record_donation(amount)
                        response = self.harpy.respond_to_donate(
                            viewer_session.username, donate_message, amount
                        )
                        self.broadcast_event(f"💰 {viewer_session.username} donated {amount}! \"{donate_message}\"")
                        self.broadcast_event(f"{self.harpy.name}: {response}")
    
                    elif message_type == MESSAGE_SUBSCRIBE:
                        viewer_session.record_subscribe()
                        response = self.harpy.respond_to_subscribe(viewer_session.username)
                        self.broadcast_event(f"⭐ {viewer_session.username} just subscribed!")
                        self.broadcast_event(f"{self.harpy.name}: {response}")
    
                    elif message_type == MESSAGE_LIKE:
                        viewer_session.record_like()
                        response = self.harpy.respond_to_like(viewer_session.username)
                        if response is not None:
                            self.broadcast_event(f"❤️ {viewer_session.username} liked the stream!")
                            self.broadcast_event(f"{self.harpy.name}: {response}")
                        # None = Harpy didn't notice, nothing broadcast
                    else:
                        send_message(client_socket, MESSAGE_ERROR, {
                            "message": f"Unknown interaction type: {readable_type}"
                        })

            except ConnectionResetError:
                username = viewer_session.username or "unknown"
                print(f"[SERVER] Connection with viewer '{username}' was reset.")
            except Exception as error:
                username = viewer_session.username or "unknown"
                print(f"[SERVER] Error with viewer '{username}': {error}")
            finally:
                with self.client_lock:
                    if client_socket in self.connected_clients:
                        del self.connected_clients[client_socket]
                    remaining_viewers = len(self.connected_clients)
    
                client_socket.close()
                username = viewer_session.username or "unknown"
                print(f"[SERVER] Viewer '{username}' disconnected. Viewers: {remaining_viewers}")
    
                if viewer_session.has_username():
                    self.broadcast_event(
                        f"{viewer_session.username} left the stream. ({remaining_viewers} viewers)"
                    )
    
    # ====================================================================================================
    # @brief: Broadcast a message to all connected clients, optionally excluding one client.
    # @param:
        # message: The string message to broadcast to all clients.
        # exclude: An optional socket object to exclude from the broadcast (e.g., the sender).  
    # ====================================================================================================
    def broadcast_event(self, message: str, exclude: socket.socket = None):
            with self.client_lock:
                clients_snapshot = dict(self.connected_clients)
    
            for client_socket in clients_snapshot:
                if client_socket is not exclude:
                    try:
                        send_message(client_socket, MESSAGE_EVENT, {
                            "sender": self.harpy.name,
                            "message": message,
                            "mood": self.harpy.current_mood
                        })
                    except Exception:
                        pass