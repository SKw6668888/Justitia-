// Shard mapping utilities for deterministic address-to-shard mapping
package utils

import (
	"crypto/sha256"
	"encoding/binary"
)

// ShardForAddress computes the shard ID for a given address using deterministic hashing
// Uses SHA-256 for cryptographic determinism (same across all nodes)
// address: the account address (string)
// numShards: total number of shards S
// Returns: shard ID in range [0, numShards-1]
func ShardForAddress(address Address, numShards int) int {
	if numShards <= 0 {
		return 0
	}
	
	// Use SHA-256 for deterministic hashing
	hash := sha256.Sum256([]byte(address))
	
	// Convert first 8 bytes to uint64
	hashVal := binary.BigEndian.Uint64(hash[:8])
	
	// Modulo to get shard ID
	return int(hashVal % uint64(numShards))
}

// IsCrossShard determines if a transaction is cross-shard
// sender: sender address
// recipient: recipient address
// numShards: total number of shards
// Returns: true if sender and recipient are in different shards
func IsCrossShard(sender, recipient Address, numShards int) bool {
	if numShards <= 1 {
		return false // Single shard system has no cross-shard txs
	}
	
	senderShard := ShardForAddress(sender, numShards)
	recipientShard := ShardForAddress(recipient, numShards)
	
	return senderShard != recipientShard
}

// GetTxShards returns both the source and destination shard for a transaction
// Returns: (fromShard, toShard)
func GetTxShards(sender, recipient Address, numShards int) (int, int) {
	fromShard := ShardForAddress(sender, numShards)
	toShard := ShardForAddress(recipient, numShards)
	return fromShard, toShard
}

