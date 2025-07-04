import json
import os
from blockchain.block import AQIBlock
from blockchain.chain import Blockchain

def save_chain(chain: Blockchain, filename: str = "data/blockchain.json"):
    """
    Save the full blockchain to a file in JSON format.
    """
    with open(filename, "w") as f:
        json.dump(chain.to_dict_list(), f, indent=4)
    print(f"[✅] Blockchain saved to {filename}")


def load_chain(filename: str = "data/blockchain.json") -> Blockchain:
    """
    Load the blockchain from a file and return a Blockchain object.
    If the file doesn't exist, return a new chain with genesis block.
    """
    blockchain = Blockchain()

    if not os.path.exists(filename):
        print(f"[⚠️] {filename} not found. Starting with a fresh chain.")
        return blockchain

    with open(filename, "r") as f:
        block_list = json.load(f)
        blockchain.chain = [AQIBlock.from_dict(b) for b in block_list]

    print(f"[✅] Loaded blockchain from {filename} with {len(blockchain.chain)} blocks")
    return blockchain
