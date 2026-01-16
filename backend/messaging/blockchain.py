# messaging/blockchain.py
import hashlib
import json
import time
from django.utils import timezone
import os
from django.db.models import Count
from collections import defaultdict

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
        
    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def mine_block(self, difficulty=2):
        """Simple mining with proof of work"""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        
    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }
        
    def __str__(self):
        return f"Block {self.index}: {self.hash}"


class MessageBlockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.difficulty = 2  # Adjust based on your server capacity
        self.blockchain_file = os.path.join(os.path.dirname(__file__), 'message_blockchain.json')
        self.load_chain()
        
    def create_genesis_block(self):
        return Block(0, time.time(), {
            "messages": [],
            "conversation_id": None,
            "block_type": "genesis",
            "description": "Genesis Block"
        }, "0")
    
    def get_latest_block(self):
        return self.chain[-1]
    
    def add_block(self, message_data):
        previous_block = self.get_latest_block()
        new_index = previous_block.index + 1
        new_timestamp = time.time()
        new_hash = previous_block.hash
        new_block = Block(new_index, new_timestamp, message_data, new_hash)
        
        # Mine the block (simple proof of work)
        new_block.mine_block(self.difficulty)
        
        # Verify block before adding
        if self.is_valid_new_block(new_block, previous_block):
            self.chain.append(new_block)
            self.save_chain()
            return new_block
        return None
    
    def is_valid_new_block(self, new_block, previous_block):
        if previous_block.index + 1 != new_block.index:
            return False
        if previous_block.hash != new_block.previous_hash:
            return False
        if new_block.calculate_hash() != new_block.hash:
            return False
        return True
    
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            if current_block.hash != current_block.calculate_hash():
                return False
            if current_block.previous_hash != previous_block.hash:
                return False
        return True
    
    def save_chain(self):
        """Persist blockchain to a file"""
        chain_data = [block.to_dict() for block in self.chain]
        try:
            with open(self.blockchain_file, 'w') as f:
                json.dump(chain_data, f, indent=4)
        except Exception as e:
            print(f"Error saving blockchain: {e}")
    
    def load_chain(self):
        """Load blockchain from file if it exists"""
        try:
            if os.path.exists(self.blockchain_file):
                with open(self.blockchain_file, 'r') as f:
                    chain_data = json.load(f)
                
                # Recreate chain from saved data
                self.chain = []
                for block_data in chain_data:
                    block = Block(
                        block_data['index'],
                        block_data['timestamp'],
                        block_data['data'],
                        block_data['previous_hash']
                    )
                    block.nonce = block_data['nonce']
                    block.hash = block_data['hash']
                    self.chain.append(block)
                
                # Validate the loaded chain
                if not self.is_chain_valid():
                    print("Warning: Loaded blockchain is invalid!")
                    self.chain = [self.create_genesis_block()]
        except Exception as e:
            print(f"Error loading blockchain, creating new one: {e}")
            self.chain = [self.create_genesis_block()]
    
    def get_conversation_blocks(self, conversation_id):
        """Get all blocks related to a specific conversation"""
        conversation_blocks = []
        for block in self.chain:
            if block.data.get("conversation_id") == str(conversation_id):
                conversation_blocks.append(block)
        return conversation_blocks
    
    def get_conversation_stats(self):
        """Get statistics about conversations in the blockchain"""
        stats = defaultdict(lambda: {"block_count": 0, "message_count": 0, "first_block": None, "last_block": None})
        
        for block in self.chain:
            if block.index == 0:  # Skip genesis block
                continue
                
            conv_id = block.data.get("conversation_id")
            if not conv_id:
                continue
                
            stats[conv_id]["block_count"] += 1
            stats[conv_id]["message_count"] += len(block.data.get("messages", []))
            
            if stats[conv_id]["first_block"] is None or block.index < stats[conv_id]["first_block"]:
                stats[conv_id]["first_block"] = block.index
                
            if stats[conv_id]["last_block"] is None or block.index > stats[conv_id]["last_block"]:
                stats[conv_id]["last_block"] = block.index
        
        return dict(stats)


# Global blockchain instance
message_blockchain = MessageBlockchain()

def record_conversation_message(message):
    """Store message hash in blockchain for integrity verification, organized by conversation"""
    # Extract message information
    message_content = message.decrypt_message() if hasattr(message, 'decrypt_message') else str(message.encrypted_content)
    message_hash = hashlib.sha256(message_content.encode()).hexdigest()
    
    block_data = {
        "block_type": "message",
        "conversation_id": str(message.conversation.id),
        "conversation_name": message.conversation.name if hasattr(message.conversation, 'name') else "Direct Message",
        "timestamp": timezone.now().timestamp(),
        "messages": [{
            "message_id": str(message.id),
            "sender_id": message.sender.id,
            "sender_username": message.sender.username,
            "content_hash": message_hash,
            "has_signature": hasattr(message, 'signature') and bool(message.signature),
            "is_encrypted": getattr(message, 'is_encrypted', False),
            "media_type": getattr(message, 'media_type', 'none'),
            "timestamp": timezone.now().timestamp(),
        }]
    }
    
    # Add to blockchain
    new_block = message_blockchain.add_block(block_data)
    
    return new_block.hash if new_block else None

def verify_message_integrity(message):
    """Verify a message hasn't been tampered with by checking blockchain"""
    if not hasattr(message, 'blockchain_hash') or not message.blockchain_hash:
        return False
    
    # Calculate current message hash
    message_content = message.decrypt_message() if hasattr(message, 'decrypt_message') else str(message.encrypted_content)
    current_hash = hashlib.sha256(message_content.encode()).hexdigest()
    
    # Find the block containing this message
    for block in message_blockchain.chain:
        for msg_data in block.data.get("messages", []):
            if msg_data.get("message_id") == str(message.id):
                # Compare with stored hash
                return current_hash == msg_data.get("content_hash")
    
    return False

def get_blockchain_explorer_data():
    """Get blockchain data for the admin explorer view"""
    return [block.to_dict() for block in message_blockchain.chain]

def get_conversation_blockchain_data(conversation_id):
    """Get blockchain data for a specific conversation"""
    blocks = message_blockchain.get_conversation_blocks(str(conversation_id))
    return [block.to_dict() for block in blocks]

def get_conversation_statistics():
    """Get statistics about conversations in the blockchain"""
    return message_blockchain.get_conversation_stats()

def validate_conversation_integrity(conversation_id):
    """Validate the integrity of all messages in a conversation"""
    from messaging.models import Message
    
    # Get all messages in the conversation
    messages = Message.objects.filter(conversation_id=conversation_id)
    
    # Verify each message against the blockchain
    results = {
        "total_messages": messages.count(),
        "verified_count": 0,
        "unverified_count": 0,
        "missing_from_blockchain": 0,
        "details": []
    }
    
    for message in messages:
        # Skip messages without blockchain records
        if not message.blockchain_hash:
            results["missing_from_blockchain"] += 1
            results["details"].append({
                "message_id": str(message.id),
                "status": "missing_from_blockchain"
            })
            continue
        
        # Verify message integrity
        is_verified = verify_message_integrity(message)
        
        if is_verified:
            results["verified_count"] += 1
            results["details"].append({
                "message_id": str(message.id),
                "status": "verified"
            })
        else:
            results["unverified_count"] += 1
            results["details"].append({
                "message_id": str(message.id),
                "status": "integrity_failed"
            })
    
    return results