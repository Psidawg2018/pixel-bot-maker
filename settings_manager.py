import json
import os

class SettingsManager:
    def __init__(self, settings_file='settings.json'):
        self.settings_file = settings_file
        self.settings = {}
        self.default_settings = {
            "theme": "dark",
            "hide_bot_default": True,
            "hotkey": "F9",
            "image_similarity_threshold": 0.9,
            "default_wait_times": {
                "type": "Fixed",
                "fixed_time": 1.0,
                "min_time": 1.0,
                "max_time": 2.0
            },
            "sequence_load_history": {}
        }
        self.load_settings()

    def load_settings(self):
        """Loads settings from the file, or uses defaults if the file doesn't exist or is invalid."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
                # Ensure all default keys from the latest version are present
                for key, value in self.default_settings.items():
                    if key not in self.settings:
                        self.settings[key] = value
                    # Also check for nested keys
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if sub_key not in self.settings[key]:
                                self.settings[key][sub_key] = sub_value
            except (json.JSONDecodeError, IOError):
                self.settings = self.default_settings
        else:
            self.settings = self.default_settings

        # Save to create the file if it didn't exist or to add new default keys
        self.save_settings()

    def save_settings(self):
        """Saves the current settings to the file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def get_setting(self, key):
        """Gets a specific setting value."""
        return self.settings.get(key)

    def set_setting(self, key, value):
        """Sets a specific setting value and saves it."""
        self.settings[key] = value
        self.save_settings()

    def increment_sequence_load_count(self, filepath):
        """Increments the load count for a given sequence file."""
        history = self.get_setting('sequence_load_history')
        # Use a normalized path to avoid duplicate entries
        normalized_path = os.path.abspath(filepath)
        history[normalized_path] = history.get(normalized_path, 0) + 1
        self.set_setting('sequence_load_history', history)

    def get_most_loaded_sequences(self, count=3):
        """Returns a list of the most frequently loaded sequences."""
        history = self.get_setting('sequence_load_history')
        if not history:
            return []

        # Sort by load count (the second item in the tuple) in descending order
        sorted_sequences = sorted(history.items(), key=lambda item: item[1], reverse=True)

        return sorted_sequences[:count]
