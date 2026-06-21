"""
@file: client/main.py

the main entry point of the client, which will connect to the server and start the chat loop.

note: requires the server to be running before starting the client, otherwise it will 
      fail to connect.
"""

from network import WarkopClient

"""
    @brief: The main function that initializes the WarkopClient, connects to the server, 
            and starts the chat loop.
"""
def main():
    # make sure the host and port match the server's host and port
    warkop_client = WarkopClient(host='localhost', port=3012)
    warkop_client.connect_to_server()

if __name__ == "__main__":
    main()