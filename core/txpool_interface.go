// TxPool interface - allows different transaction pool implementations
package core

import "blockEmulator/utils"

// TxPoolInterface defines the common interface for transaction pools
// This allows switching between FIFO (TxPool) and Priority (PriorityTxPool) implementations
type TxPoolInterface interface {
	// Add a single transaction to the pool
	AddTx2Pool(tx *Transaction)

	// Add multiple transactions to the pool
	AddTxs2Pool(txs []*Transaction)

	// Pack transactions for block proposal (by transaction count)
	PackTxs(max_txs uint64) []*Transaction

	// Pack transactions for block proposal (by byte size)
	PackTxsWithBytes(max_bytes int) []*Transaction

	// Add a relay transaction to the relay pool for a specific shard
	AddRelayTx(tx *Transaction, shardID uint64)

	// Lock the pool
	GetLocked()

	// Unlock the pool
	GetUnlocked()

	// Get the number of transactions in the queue
	GetTxQueueLen() int

	// Clear the relay pool
	ClearRelayPool()

	// Pack relay transactions from the relay pool
	PackRelayTxs(shardID, minRelaySize, maxRelaySize uint64) ([]*Transaction, bool)

	// Transfer transactions when re-sharding
	TransferTxs(addr utils.Address) []*Transaction
	
	// Filter transactions based on a custom function (for CLPA account transfer)
	// Returns: filtered transactions that match the condition, remaining transactions stay in pool
	FilterTxs(filter func(*Transaction) bool) []*Transaction
	
	// Initialize/Reset the relay pool
	InitRelayPool()
	
	// Get relay transactions for a specific shard
	GetRelayPoolTxs(shardID uint64) []*Transaction
}
