# ====================================================================================================
# @file: broadcast_engine.py
#
# runs in a separate thread and allows harpy to "talk to herself" at random intervals
# ====================================================================================================
import threading
import random
import time

class BroadcastEngine:

    # ====================================================================================================
    # @brief: Initialize the broadcast engine.
    # @param:
    #       character_engine: The CharacterEngine instance to generate lines from
    #       broadcast_callback: A function that takes a string and sends it to all viewers.
    #                            This will be the server's broadcast_event() method.
    # ====================================================================================================

    def __init__(self, character_engine, broadcast_callback):
        self.character_engine = character_engine
        self.broadcast_callback = broadcast_callback
        min_interval, max_interval = character_engine.get_broadcast_interval
        self.min_interval = min_interval
        self.max_interval = max_interval

        self.is_running = False
        self.is_paused = False
        self.broadcast_thread = None

    # ====================================================================================================
    # @brief: start the broadcast loop in a background thread.
    # ====================================================================================================
    def start_broadcast(self):
        self.is_running = True
        self.broadcast_thread = threading.Thread(target=self.broadcast_loop, daemon=True)
        self.broadcast_thread.start()
        print(f"[BROADCAST] Harpy's commentary engine started\n")
        print(f"(Interval: {self.min_interval}-{self.max_interval}s)")

    # ====================================================================================================
    # @brief: stops broadcast loop
    # ====================================================================================================
    def stop_broadcast(self):
        self.is_running = False

    # ====================================================================================================
    # @brief: temporarily pause broadcasting and let harpy react to viewer
    # @param:
    #       pause_duration: How many seconds to pause for (set to 3 second for now)
    # ====================================================================================================
    def pause_briefly(self, pause_duration: float = 3.0):
        self.is_paused = True
        # unpause
        def unpause():
            time.sleep(pause_duration)
            self.is_paused = False
        # this runs in a separate thread. caller wont be blocked
        threading.Thread(target=unpause, daemon=True).start()

    def broadcast_loop(self):
        while self.is_running:
            # sleep in a random interval and in a small increment
            wait_time = random.uniform(self.min_interval, self.max_interval)
            elapsed = 0
            while elapsed < wait_time and self.is_running:
                time.sleep(0.5)
                elapsed += 0.5

            if not self.is_running:
                break
            # skips broadcast if harpy is responding to a viewer
            if self.is_paused:
                continue
            # generate a commentary line and shift harpy's mood each broadcast (maybe?)
            commentary = self.character_engine.generate_broadcast()
            self.broadcast_callback(commentary)
            new_mood = self.character_engine.shift_mood()