from blockchain.block import AQIBlock

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        data = {
        "deviceId": "genesis",
        "aqi": 0,
        "temperature": 0,
        "humidity": 0,
        "location": {"lat": 0.0, "lon": 0.0}
    }
        return AQIBlock(index=0, data=data, previous_hash="0")

    def get_latest_block(self):
        # Return the most recent block
        return self.chain[-1]

    def add_block(self, data):
        # Add a new block using the last block’s hash
        latest_block = self.get_latest_block()
        new_index = latest_block.index + 1
        new_block = AQIBlock(index=new_index, data=data, previous_hash=latest_block.hash)
        self.chain.append(new_block)

    def is_chain_valid(self):
        # Check if the chain has been tampered with
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Recalculate current block’s hash and compare
            if current.hash != current.calculate_hash():
                return False

            # Check if it properly links to the previous block
            if current.previous_hash != previous.hash:
                return False

        return True

    def to_dict_list(self):
        # Convert the full chain to a list of dictionaries
        return [block.to_dict() for block in self.chain]
