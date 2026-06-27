# ====================================================================================================
# @file: bridge/ws_bridge.py

# WebSocket-to-TCP bridge for Harpy's stream.

# translator between the browser (React app) and the TCP server.
# It does two things simultaneously: 
#   1. Runs a WebSocket server (port 8765) that browsers connect to
#   2. For each browser connection, opens a TCP connection to the stream server (port 3012)
# ====================================================================================================

import asyncio
import json
import sys
import os
import struct
import websockets

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.protocol import (
    HEADER_FORMAT, HEADER_SIZE, ENCODING,
    MESSAGE_NAMES, MESSAGE_WELCOME, MESSAGE_USERNAME, MESSAGE_USERNAME_ACK,
    MESSAGE_CHAT, MESSAGE_REPLY, MESSAGE_EVENT, MESSAGE_QUIT, MESSAGE_ERROR,
    MESSAGE_GIFT, MESSAGE_DONATE, MESSAGE_SUBSCRIBE, MESSAGE_LIKE
)

# Server connection settings
TCP_HOST = 'localhost'
TCP_PORT = 3012
WS_HOST = 'localhost'
WS_PORT = 8765


# ====================================================================================================
# HELPER FUNCTIONS
# ====================================================================================================

async def tcp_send_message(reader_writer, message_type: int, payload: dict):
    writer = reader_writer[1]
    payload_bytes = json.dumps(payload).encode(ENCODING)
    header = struct.pack(HEADER_FORMAT, len(payload_bytes), message_type)
    writer.write(header + payload_bytes)
    await writer.drain()


async def tcp_receive_message(reader_writer) -> tuple:
    reader = reader_writer[0]
    try:
        header_data = await reader.readexactly(HEADER_SIZE)
    except (asyncio.IncompleteReadError, ConnectionError):
        return None, None

    payload_length, message_type = struct.unpack(HEADER_FORMAT, header_data)

    try:
        payload_data = await reader.readexactly(payload_length)
    except (asyncio.IncompleteReadError, ConnectionError):
        return None, None

    payload = json.loads(payload_data.decode(ENCODING))
    return message_type, payload


# ====================================================================================================
# @brief: Handle one browser client.
#
# For each browser that connects via WebSocket:
# 1. Open a TCP connection to the stream server
# 2. Forward the WELCOME message from TCP → WebSocket
# 3. Start two concurrent tasks:
#    a. tcp_to_ws: reads from TCP, sends to WebSocket (server → browser)
#    b. ws_to_tcp: reads from WebSocket, sends to TCP (browser → server)
# 4. When either side disconnects, clean up both connections
# ====================================================================================================

async def handle_browser_client(websocket):
    tcp_connection = None
    client_address = websocket.remote_address
    print(f"[BRIDGE] Browser connected from {client_address}")

    try:
        # open connection
        reader, writer = await asyncio.open_connection(TCP_HOST, TCP_PORT)
        tcp_connection = (reader, writer)
        print(f"[BRIDGE] TCP connection established for {client_address}")

        # Receive WELCOME from TCP server and forward to browser
        message_type, payload = await tcp_receive_message(tcp_connection)
        if message_type == MESSAGE_WELCOME:
            await websocket.send(json.dumps({
                "type": MESSAGE_NAMES.get(message_type, "UNKNOWN"),
                "payload": payload
            }))

        # Wait for browser to send username
        raw_message = await websocket.recv()
        browser_message = json.loads(raw_message)

        if browser_message.get("type") == "USERNAME":
            username = browser_message.get("payload", {}).get("username", "anonymous")
            await tcp_send_message(tcp_connection, MESSAGE_USERNAME, {
                "username": username
            })
            print(f"[BRIDGE] Viewer '{username}' registered from browser")

            # forward USERNAME_ACK to browser
            message_type, payload = await tcp_receive_message(tcp_connection)
            if message_type is not None:
                await websocket.send(json.dumps({
                    "type": MESSAGE_NAMES.get(message_type, "UNKNOWN"),
                    "payload": payload
                }))

        # start bidirectional forwarding
        tcp_to_ws_task = asyncio.create_task(forward_tcp_to_ws(tcp_connection, websocket))
        ws_to_tcp_task = asyncio.create_task(forward_ws_to_tcp(websocket, tcp_connection))

        done, pending = await asyncio.wait(
            [tcp_to_ws_task, ws_to_tcp_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel the other task
        for task in pending:
            task.cancel()

    except websockets.exceptions.ConnectionClosed:
        print(f"[BRIDGE] Browser {client_address} disconnected")
    except ConnectionRefusedError:
        print(f"[BRIDGE] Cannot connect to TCP server — is it running on {TCP_HOST}:{TCP_PORT}?")
        try:
            await websocket.send(json.dumps({
                "type": "ERROR",
                "payload": {"message": "Stream server is not running!"}
            }))
        except Exception:
            pass
    except Exception as error:
        print(f"[BRIDGE] Error with {client_address}: {error}")
    finally:
        # Clean up TCP connection
        if tcp_connection:
            writer = tcp_connection[1]
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        print(f"[BRIDGE] Cleaned up connections for {client_address}")


# ====================================================================================================
# @brief: Forward messages from TCP server to browser WebSocket.
#         Converts binary protocol messages to JSON.
# ====================================================================================================

async def forward_tcp_to_ws(tcp_connection, websocket):
    try:
        while True:
            message_type, payload = await tcp_receive_message(tcp_connection)

            if message_type is None:
                print("[BRIDGE] TCP server closed connection")
                break

            type_name = MESSAGE_NAMES.get(message_type, f"UNKNOWN({message_type})")

            await websocket.send(json.dumps({
                "type": type_name,
                "payload": payload
            }))

    except websockets.exceptions.ConnectionClosed:
        print("[BRIDGE] Browser disconnected (tcp_to_ws)")
    except Exception as error:
        print(f"[BRIDGE] Error in tcp_to_ws: {error}")


# ====================================================================================================
# @brief: Forward messages from browser WebSocket to TCP server.
#         Converts JSON messages to binary protocol.
#
# ====================================================================================================

# Map type name strings back to message type bytes
TYPE_NAME_TO_CODE = {name: code for code, name in MESSAGE_NAMES.items()}

async def forward_ws_to_tcp(websocket, tcp_connection):
    try:
        async for raw_message in websocket:
            browser_message = json.loads(raw_message)
            type_name = browser_message.get("type", "")
            payload = browser_message.get("payload", {})

            # Convert type name back to byte code
            message_code = TYPE_NAME_TO_CODE.get(type_name)

            if message_code is not None:
                await tcp_send_message(tcp_connection, message_code, payload)
            else:
                print(f"[BRIDGE] Unknown message type from browser: {type_name}")

    except websockets.exceptions.ConnectionClosed:
        print("[BRIDGE] Browser disconnected (ws_to_tcp)")
    except Exception as error:
        print(f"[BRIDGE] Error in ws_to_tcp: {error}")


# ====================================================================================================
# @brief: Start the WebSocket server.
# ====================================================================================================

async def main():
    print(f"[BRIDGE] Starting WebSocket bridge...")
    print(f"[BRIDGE] TCP server: {TCP_HOST}:{TCP_PORT}")
    print(f"[BRIDGE] WebSocket server: ws://{WS_HOST}:{WS_PORT}")
    print(f"[BRIDGE] Waiting for browser connections...\n")

    async with websockets.serve(handle_browser_client, WS_HOST, WS_PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[BRIDGE] Bridge shutting down.")