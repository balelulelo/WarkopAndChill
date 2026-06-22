# ====================================================================================================
# @file: character_engine.py
#
# the main brain for the character (harpy). loads personality config
# from JSON and generates response
# ====================================================================================================
import json
import random
import os

class CharacterEngine:

    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as config_file:
            self.character_data = json.load(config_file)

        self.name = self.character_data["name"]
        self.current_mood = self.character_data["default_mood"]
        self.gift_threshold = self.character_data.get("gift_threshold", 500000)

    # ====================================================================================================
    # @brief: generate welpcome message for incoming viewer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
    # ====================================================================================================  
    def generate_welcome(self, username: str) -> str:
        template = self.character_data["welcome_message"]
        return template.format(username=username)
    
    # ====================================================================================================
    # @brief: generate goodbve messagefor leaving viewer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
    # ====================================================================================================
    def generate_goodbye(self, username: str) -> str:
        template = self.character_data["goodbye_message"]
        return template.format(username=username)
    
     # ====================================================================================================
    # @brief: Generate a response to a chat message.
    # @param: 
    #       username: The viewer's display name
    #       message: What the viewer said (currently unused, but ready for 
    #                keyword matching in future iterations)
    # @return: Harpy's response string
    # ====================================================================================================
    def respond_to_chat(self, username: str, message: str) -> str:
        mood_responses = self.character_data["responses"]["chat"].get(
            self.current_mood, 
            self.character_data["responses"]["chat"]["chaotic"]
        )
        template = random.choice(mood_responses)
        return template.format(username=username)
 
    # ====================================================================================================
    # @brief: Generate a response to a gift.
    # @param: 
    #       username: The viewer's display name
    #       amount: The gift value (compared against gift_threshold_big)
    # @return: Harpy's response string
    # ====================================================================================================
    def respond_to_gift(self, username: str, amount: int) -> str:
        if amount >= self.gift_threshold_big:
            gift_pool = self.character_data["responses"]["gift"]["big"]
        else:
            gift_pool = self.character_data["responses"]["gift"]["small"]
 
        template = random.choice(gift_pool)
        return template.format(username=username)
 
    # ====================================================================================================
    # @brief: Generate a response to a donation (which includes a message from the viewer).
    # @param: 
    #       username: The viewer's display name
    #       donate_message: The text message attached to the donation
    #       amount: The donation amount
    # @return: Harpy's response string
    # ====================================================================================================
    def respond_to_donate(self, username: str, donate_message: str, amount: int) -> str:
        donate_pool = self.character_data["responses"]["donate"]
        template = random.choice(donate_pool)
        return template.format(username=username, donate_message=donate_message)
 
    # ====================================================================================================
    # @brief: Generate a response to a new subscriber.
    # @param username: The viewer's display name
    # @return: Harpy's response string
    # ====================================================================================================
    def respond_to_subscribe(self, username: str) -> str:
        subscribe_pool = self.character_data["responses"]["subscribe"]
        template = random.choice(subscribe_pool)
        return template.format(username=username)
 
    # ====================================================================================================
    # @brief: Generate a response to a like, or return None if Harpy doesn't notice it.
    # @param: 
    #       username: The viewer's display name
    # @return: Harpy's response string, or None if she didn't notice
    # ====================================================================================================
    def respond_to_like(self, username: str) -> str | None:
        # 40% chance Harpy notices the like
        if random.random() < 0.4:
            noticed_pool = self.character_data["responses"]["like"]["noticed"]
            template = random.choice(noticed_pool)
            return template.format(username=username)
        else:
            return None  
 
    # ====================================================================================================
    # @brief: Get a random broadcast line (Harpy's live commentary).
    # @return: A broadcast commentary string
    # ====================================================================================================
    def generate_broadcast(self) -> str:
        scripts = self.character_data["broadcast_scripts"]
        # random: 60% gaming, 25% random tangent, 15% wholesome
        roll = random.random()
        if roll < 0.60:
            pool = scripts["gaming"]
        elif roll < 0.85:
            pool = scripts["random_tangents"]
        else:
            pool = scripts["wholesome_moments"]
 
        return random.choice(pool)
 
    # ====================================================================================================
    # @brief: Get the broadcast interval range
    # @return: Tuple of (min_seconds, max_seconds)
    # ====================================================================================================
    def get_broadcast_interval(self) -> tuple:
        interval_config = self.character_data["broadcast_interval_seconds"]
        return interval_config["min"], interval_config["max"]
 
    # ====================================================================================================
    # @brief: Change Harpy's current mood.
    # @param: 
    #       new_mood: One of: "hyped", "focused", "tilted", "chill", "chaotic"
    # ====================================================================================================
    def set_mood(self, new_mood: str):
        if new_mood in self.character_data["moods"]:
            self.current_mood = new_mood
 
    # ====================================================================================================
    # @brief: Randomly shift Harpy's mood. Called periodically to keep the stream dynamic.
    # @return: The new mood (or the same mood if it didn't change)
    # ====================================================================================================
    def shift_mood(self) -> str:
        # 30% chance of the mood changes due to her "unpredictable personality"
        if random.random() < 0.3:
            available_moods = self.character_data["moods"]
            self.current_mood = random.choice(available_moods)
        return self.current_mood
 
