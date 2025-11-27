package message

import (
	"math/big"
	"time"
)

// Message type for fee synchronization across shards
const (
	CFeeInfoSync MessageType = "FeeInfoSync"
)

// FeeInfoSync is sent by each shard to broadcast its average ITX fee E(f_s)
// This enables cross-shard subsidy calculation in multi-process architecture
type FeeInfoSync struct {
	ShardID     uint64    // ID of the shard reporting fee info
	AvgITXFee   *big.Int  // E(f_s): Average ITX fee for this shard
	BlockHeight uint64    // Current block height when this info was generated
	Timestamp   time.Time // When this info was generated
}

// NewFeeInfoSync creates a new fee info sync message
func NewFeeInfoSync(shardID uint64, avgFee *big.Int, blockHeight uint64) *FeeInfoSync {
	return &FeeInfoSync{
		ShardID:     shardID,
		AvgITXFee:   new(big.Int).Set(avgFee), // Make a copy to avoid concurrent modification
		BlockHeight: blockHeight,
		Timestamp:   time.Now(),
	}
}
