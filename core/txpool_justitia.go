// Justitia-enabled transaction pool with priority queue
package core

import (
	"blockEmulator/utils"
	"container/heap"
	"sync"
	"time"
)

// PriorityTxPool implements a transaction pool with Justitia incentive mechanism
// Cross-shard transactions with rewards are prioritized
type PriorityTxPool struct {
	TxQueue   *TxPriorityQueue          // priority queue for transactions
	RelayPool map[uint64][]*Transaction // designed for sharded blockchain, from Monoxide
	lock      sync.Mutex
}

// TxPriorityQueue implements heap.Interface for transaction prioritization
type TxPriorityQueue []*Transaction

func (pq TxPriorityQueue) Len() int { return len(pq) }

func (pq TxPriorityQueue) Less(i, j int) bool {
	// Higher priority if:
	// 1. Cross-shard transaction with Justitia reward
	// 2. Higher reward value
	// 3. Earlier timestamp (FIFO for same priority)

	txI, txJ := pq[i], pq[j]

	// If one is cross-shard with reward and the other is not, prioritize the cross-shard
	if txI.IsCrossShard && txI.JustitiaReward > 0 && (!txJ.IsCrossShard || txJ.JustitiaReward == 0) {
		return true
	}
	if txJ.IsCrossShard && txJ.JustitiaReward > 0 && (!txI.IsCrossShard || txI.JustitiaReward == 0) {
		return false
	}

	// Both are cross-shard with rewards, compare reward values
	if txI.IsCrossShard && txJ.IsCrossShard && txI.JustitiaReward != txJ.JustitiaReward {
		return txI.JustitiaReward > txJ.JustitiaReward
	}

	// Same priority level, use FIFO (earlier time has higher priority)
	return txI.Time.Before(txJ.Time)
}

func (pq TxPriorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
}

func (pq *TxPriorityQueue) Push(x interface{}) {
	item := x.(*Transaction)
	*pq = append(*pq, item)
}

func (pq *TxPriorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil // avoid memory leak
	*pq = old[0 : n-1]
	return item
}

// NewPriorityTxPool creates a new transaction pool with Justitia support
func NewPriorityTxPool() *PriorityTxPool {
	pq := make(TxPriorityQueue, 0)
	heap.Init(&pq)
	return &PriorityTxPool{
		TxQueue:   &pq,
		RelayPool: make(map[uint64][]*Transaction),
	}
}

// AddTx2Pool adds a transaction to the priority pool
func (txpool *PriorityTxPool) AddTx2Pool(tx *Transaction) {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	if tx.Time.IsZero() {
		tx.Time = time.Now()
	}
	// Save original time for Justitia mechanism (only if not already set)
	if tx.OriginalPropTime.IsZero() {
		tx.OriginalPropTime = tx.Time
	}
	heap.Push(txpool.TxQueue, tx)
}

// AddTxs2Pool adds multiple transactions to the pool
func (txpool *PriorityTxPool) AddTxs2Pool(txs []*Transaction) {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	for _, tx := range txs {
		if tx.Time.IsZero() {
			tx.Time = time.Now()
		}
		// Save original time for Justitia mechanism (only if not already set)
		if tx.OriginalPropTime.IsZero() {
			tx.OriginalPropTime = tx.Time
		}
		heap.Push(txpool.TxQueue, tx)
	}
}

// PackTxs packs transactions from the priority queue
// Transactions are automatically sorted by priority (cross-shard with rewards first)
func (txpool *PriorityTxPool) PackTxs(max_txs uint64) []*Transaction {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()

	txNum := max_txs
	if uint64(txpool.TxQueue.Len()) < txNum {
		txNum = uint64(txpool.TxQueue.Len())
	}

	txs_Packed := make([]*Transaction, 0, txNum)
	for i := uint64(0); i < txNum; i++ {
		if txpool.TxQueue.Len() > 0 {
			tx := heap.Pop(txpool.TxQueue).(*Transaction)
			txs_Packed = append(txs_Packed, tx)
		}
	}

	return txs_Packed
}

// PackTxsWithBytes packs transactions considering byte size limit
func (txpool *PriorityTxPool) PackTxsWithBytes(max_bytes int) []*Transaction {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()

	txs_Packed := make([]*Transaction, 0)
	currentSize := 0

	for txpool.TxQueue.Len() > 0 {
		tx := heap.Pop(txpool.TxQueue).(*Transaction)
		txSize := len(tx.Encode())

		if currentSize+txSize > max_bytes {
			// Put the transaction back if it doesn't fit
			heap.Push(txpool.TxQueue, tx)
			break
		}

		txs_Packed = append(txs_Packed, tx)
		currentSize += txSize
	}

	return txs_Packed
}

// AddRelayTx adds a relay transaction to the relay pool
func (txpool *PriorityTxPool) AddRelayTx(tx *Transaction, shardID uint64) {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	_, ok := txpool.RelayPool[shardID]
	if !ok {
		txpool.RelayPool[shardID] = make([]*Transaction, 0)
	}
	txpool.RelayPool[shardID] = append(txpool.RelayPool[shardID], tx)
}

// GetLocked locks the pool
func (txpool *PriorityTxPool) GetLocked() {
	txpool.lock.Lock()
}

// GetUnlocked unlocks the pool
func (txpool *PriorityTxPool) GetUnlocked() {
	txpool.lock.Unlock()
}

// GetTxQueueLen returns the length of transaction queue
func (txpool *PriorityTxPool) GetTxQueueLen() int {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	return txpool.TxQueue.Len()
}

// ClearRelayPool clears the relay pool
func (txpool *PriorityTxPool) ClearRelayPool() {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	txpool.RelayPool = make(map[uint64][]*Transaction)
}

// PackRelayTxs packs relay transactions from relay pool
func (txpool *PriorityTxPool) PackRelayTxs(shardID, minRelaySize, maxRelaySize uint64) ([]*Transaction, bool) {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	if _, ok := txpool.RelayPool[shardID]; !ok {
		return nil, false
	}
	if len(txpool.RelayPool[shardID]) < int(minRelaySize) {
		return nil, false
	}
	txNum := maxRelaySize
	if uint64(len(txpool.RelayPool[shardID])) < txNum {
		txNum = uint64(len(txpool.RelayPool[shardID]))
	}
	relayTxPacked := txpool.RelayPool[shardID][:txNum]
	txpool.RelayPool[shardID] = txpool.RelayPool[shardID][txNum:]
	return relayTxPacked, true
}

// TransferTxs transfers transactions when re-sharding
func (txpool *PriorityTxPool) TransferTxs(addr utils.Address) []*Transaction {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	
	txTransfered := make([]*Transaction, 0)
	newQueue := make(TxPriorityQueue, 0)
	heap.Init(&newQueue)  // Initialize the new heap
	
	// Extract transactions from the priority queue
	for txpool.TxQueue.Len() > 0 {
		tx := heap.Pop(txpool.TxQueue).(*Transaction)
		if tx.Sender == addr {
			txTransfered = append(txTransfered, tx)
		} else {
			heap.Push(&newQueue, tx)
		}
	}
	
	// Handle relay pool
	newRelayPool := make(map[uint64][]*Transaction)
	for shardID, shardPool := range txpool.RelayPool {
		for _, tx := range shardPool {
			if tx.Sender == addr {
				txTransfered = append(txTransfered, tx)
			} else {
				if _, ok := newRelayPool[shardID]; !ok {
					newRelayPool[shardID] = make([]*Transaction, 0)
				}
				newRelayPool[shardID] = append(newRelayPool[shardID], tx)
			}
		}
	}
	
	txpool.TxQueue = &newQueue
	txpool.RelayPool = newRelayPool
	return txTransfered
}

// Filter transactions based on a custom function (for CLPA account transfer)
func (txpool *PriorityTxPool) FilterTxs(filter func(*Transaction) bool) []*Transaction {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	
	filtered := make([]*Transaction, 0)
	newQueue := make(TxPriorityQueue, 0)
	heap.Init(&newQueue)
	
	// Extract all transactions from priority queue
	for txpool.TxQueue.Len() > 0 {
		tx := heap.Pop(txpool.TxQueue).(*Transaction)
		if filter(tx) {
			filtered = append(filtered, tx)
		} else {
			heap.Push(&newQueue, tx)
		}
	}
	
	txpool.TxQueue = &newQueue
	return filtered
}

// Initialize/Reset the relay pool
func (txpool *PriorityTxPool) InitRelayPool() {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	txpool.RelayPool = make(map[uint64][]*Transaction)
}

// Get relay transactions for a specific shard
func (txpool *PriorityTxPool) GetRelayPoolTxs(shardID uint64) []*Transaction {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	if txs, ok := txpool.RelayPool[shardID]; ok {
		return txs
	}
	return make([]*Transaction, 0)
}
