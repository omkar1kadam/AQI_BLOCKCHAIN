import hashlib
import json
import time

class AQIBlock:
    def __init__(self, index, data, previous_hash):
        self.index = index                      # Block number (0, 1, 2, ...)
        self.timestamp = time.time()            # When this block was created
        self.data = data                        # The sensor data (AQI, temp, etc.)
        self.previous_hash = previous_hash      # Hash of the block before this one
        self.hash = self.calculate_hash()       # Hash of this block

    def calculate_hash(self):
        # We create a string of the block’s contents
        block_contents = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }

        # Convert it to a string and hash it
        block_string = json.dumps(block_contents, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        # Convert block to dictionary so we can save/send it easily
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(block_data):
        # Re-create a block from saved data (like from a file)
        block = AQIBlock(
            index=block_data["index"],
            data=block_data["data"],
            previous_hash=block_data["previous_hash"]
        )
        block.timestamp = block_data["timestamp"]
        block.hash = block_data["hash"]
        return block
