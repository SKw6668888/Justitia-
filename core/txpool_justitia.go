// Justitia-enabled transaction pool with priority queue
package core

import (
	"blockEmulator/incentive/justitia"
	"blockEmulator/utils"
	"container/heap"
	"math/big"
	"sync"
	"time"
)

// TxScheduler is an interface for transaction selection algorithms
// This avoids circular dependency with txpool/scheduler package
type TxScheduler interface {
	SelectForBlock(capacity int, txPool []*Transaction) []*Transaction
}

// PriorityTxPool implements a transaction pool with Justitia incentive mechanism
// Cross-shard transactions with rewards are prioritized
type PriorityTxPool struct {
	TxQueue   *TxPriorityQueue          // priority queue for transactions
	RelayPool map[uint64][]*Transaction // designed for sharded blockchain, from Monoxide
	lock      sync.Mutex
	
	// Justitia components (using interface to avoid circular dependency)
	scheduler TxScheduler // Justitia scheduler for transaction selection
	shardID   int         // Current shard ID
}

// TxPriorityQueue implements heap.Interface for transaction prioritization
type TxPriorityQueue []*Transaction

func (pq TxPriorityQueue) Len() int { return len(pq) }

func (pq TxPriorityQueue) Less(i, j int) bool {
	// Priority based on FeeToProposer (base fee paid by user)
	// This provides a fair baseline before Justitia scheduler applies utility-based selection
	// 
	// Note: When Justitia scheduler is active, packTxsWithScheduler will further refine
	// selection based on computed utilities (uA, uB) from Shapley value allocation
	
	txI, txJ := pq[i], pq[j]
	
	// Compare base fees (higher fee = higher priority)
	feeI := txI.FeeToProposer
	feeJ := txJ.FeeToProposer
	
	if feeI == nil {
		feeI = big.NewInt(0)
	}
	if feeJ == nil {
		feeJ = big.NewInt(0)
	}
	
	cmp := feeI.Cmp(feeJ)
	if cmp != 0 {
		return cmp > 0 // Higher fee = higher priority
	}
	
	// If fees are equal, use FIFO (earlier timestamp = higher priority)
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
		scheduler: nil, // Will be set via SetScheduler
		shardID:   -1,
	}
}

// SetScheduler sets the Justitia scheduler for this pool
// scheduler must implement TxScheduler interface
func (txpool *PriorityTxPool) SetScheduler(sched TxScheduler, shardID int) {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	txpool.scheduler = sched
	txpool.shardID = shardID
}

// GetScheduler returns the Justitia scheduler for this pool
func (txpool *PriorityTxPool) GetScheduler() TxScheduler {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	return txpool.scheduler
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

// PackTxs packs transactions from the priority queue using Justitia scheduler
// Transactions are selected based on Justitia incentive mechanism (Case1/Case2/Case3)
func (txpool *PriorityTxPool) PackTxs(max_txs uint64) []*Transaction {
	// If scheduler is available, use intelligent selection
	if txpool.scheduler != nil {
		return txpool.packTxsWithScheduler(max_txs)
	}
	
	// Otherwise use simple priority queue (backward compatibility)
	return txpool.packTxsSimple(max_txs)
}

// packTxsWithScheduler uses Justitia scheduler for transaction selection
func (txpool *PriorityTxPool) packTxsWithScheduler(max_txs uint64) []*Transaction {
	txpool.lock.Lock()
	
	// Extract all available transactions from priority queue
	allTxs := make([]*Transaction, 0, txpool.TxQueue.Len())
	for txpool.TxQueue.Len() > 0 {
		tx := heap.Pop(txpool.TxQueue).(*Transaction)
		allTxs = append(allTxs, tx)
	}
	
	txpool.lock.Unlock()
	
	// Use Justitia scheduler to select transactions intelligently
	// This handles Case1/Case2/Case3 classification and prioritization
	selected := txpool.scheduler.SelectForBlock(int(max_txs), allTxs)
	
	// Put unselected transactions back into the priority queue
	txpool.lock.Lock()
	selectedMap := make(map[string]bool)
	for _, tx := range selected {
		selectedMap[string(tx.TxHash)] = true
	}
	
	for _, tx := range allTxs {
		if !selectedMap[string(tx.TxHash)] {
			heap.Push(txpool.TxQueue, tx)
		}
	}
	txpool.lock.Unlock()
	
	return selected
}

// packTxsSimple uses simple priority queue without Justitia scheduler
func (txpool *PriorityTxPool) packTxsSimple(max_txs uint64) []*Transaction {
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

// GetMetrics returns current dynamic metrics for Justitia incentive mechanism
// This provides queue length and estimated wait time for the current shard
func (txpool *PriorityTxPool) GetMetrics() justitia.DynamicMetrics {
	txpool.lock.Lock()
	defer txpool.lock.Unlock()
	
	queueLen := int64(txpool.TxQueue.Len())
	
	// Estimate average wait time based on queue length and transaction timestamps
	// This is a rough estimate: we look at the oldest transaction in the queue
	var avgWaitTime float64 = 0.0
	
	if queueLen > 0 {
		// Find the oldest transaction in the queue
		now := time.Now()
		var oldestTime time.Time
		
		// Peek at transactions without modifying the heap
		for _, tx := range *txpool.TxQueue {
			if oldestTime.IsZero() || tx.Time.Before(oldestTime) {
				oldestTime = tx.Time
			}
		}
		
		if !oldestTime.IsZero() {
			// Average wait time = time since oldest transaction (in milliseconds)
			avgWaitTime = float64(now.Sub(oldestTime).Milliseconds())
		}
	}
	
	return justitia.DynamicMetrics{
		QueueLengthA:     queueLen,
		QueueLengthB:     0,                // Will be filled by caller if needed
		AvgWaitTimeA:     avgWaitTime,
		AvgWaitTimeB:     0.0,              // Will be filled by caller if needed
		CurrentInflation: big.NewInt(0),    // Will be filled by caller if needed
	}
}
