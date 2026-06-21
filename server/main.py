# ====================================================================================================
# @file: server/main.py

# the main entry point of the server, which will start the server 
# and listen for incoming requests.
# ====================================================================================================

from server import WarkopServer

# ====================================================================================================
    # @brief: The main function that initializes and starts the WarkopServer.
# ====================================================================================================
def main():
    warkop_server = WarkopServer(host='localhost', port=3012)
    warkop_server.start_server()

if __name__ == "__main__":
    main()