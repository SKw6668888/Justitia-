// Package ethcsv provides utilities for parsing and processing Ethereum CSV transaction data
package ethcsv

import (
	"blockEmulator/utils"
	"crypto/sha256"
	"encoding/binary"
	"math/big"
	"strings"
)

// TxRow represents a transaction row from the Ethereum CSV dataset
type TxRow struct {
	BlockNumber          uint64
	Timestamp            uint64
	TxHash               string
	From                 string
	To                   string
	ToCreate             string // Contract creation address
	Value                *big.Int
	GasLimit             uint64
	GasPrice             *big.Int // For legacy/EIP-2930 transactions
	GasUsed              uint64
	EIP2718Type          uint8 // 0=legacy, 1=EIP-2930, 2=EIP-1559, 3=EIP-4844
	BaseFeePerGas        *big.Int
	MaxFeePerGas         *big.Int
	MaxPriorityFeePerGas *big.Int
	IsError              bool
	BlobHashes           []string // EIP-4844 blob hashes
	BlobBaseFeePerGas    *big.Int // EIP-4844 blob base fee
	BlobGasUsed          uint64   // EIP-4844 blob gas used
}

// ComputeProposerFee returns the proposer (block builder) revenue in wei.
// DO NOT include baseFee burns. For EIP-1559, only the tip is paid to the proposer.
// This is the ONLY source of truth for computing proposer fees.
func ComputeProposerFee(r TxRow) *big.Int {
	zero := big.NewInt(0)
	
	// No gas used means no fee
	if r.GasUsed == 0 {
		return zero
	}
	
	gu := new(big.Int).SetUint64(r.GasUsed)
	
	switch r.EIP2718Type {
	case 0, 1: // Legacy (type 0) and EIP-2930 (type 1)
		// For legacy transactions: proposer gets gasUsed * gasPrice
		if r.GasPrice == nil {
			return zero
		}
		// fee = gasUsed * gasPrice
		return new(big.Int).Mul(gu, r.GasPrice)
		
	case 2, 3: // EIP-1559 (type 2) and EIP-4844 (type 3)
		// For EIP-1559 and blob transactions: proposer only gets the tip, not the base fee
		// For type 3, this calculates the fee from regular execution gas (not blob gas)
		if r.BaseFeePerGas == nil || r.MaxFeePerGas == nil || r.MaxPriorityFeePerGas == nil {
			return zero
		}
		
		// effectiveGasPrice = min(maxFeePerGas, baseFeePerGas + maxPriorityFeePerGas)
		sum := new(big.Int).Add(r.BaseFeePerGas, r.MaxPriorityFeePerGas)
		effective := new(big.Int).Set(r.MaxFeePerGas)
		if sum.Cmp(effective) < 0 {
			effective = sum
		}
		
		// tip = max(effectiveGasPrice - baseFeePerGas, 0)
		tip := new(big.Int).Sub(effective, r.BaseFeePerGas)
		if tip.Sign() < 0 {
			tip = zero
		}
		
		// proposerFee = gasUsed * tip (for regular execution gas)
		// NOTE: For type 3 (blob txs), blob gas fees are separate:
		// - Blob base fee is burned (like regular base fee)
		// - Blob tip would require maxFeePerBlobGas / maxPriorityFeePerBlobGas fields
		// - Since we don't have those fields in the dataset, we only count execution gas tip
		return new(big.Int).Mul(gu, tip)
		
	default:
		// Future transaction types: return zero to be conservative
		return zero
	}
}

// ToAddress returns the destination address for this transaction.
// For contract creation, returns the ToCreate address.
// For regular transactions, returns the To address.
func ToAddress(r TxRow) string {
	if r.To != "" {
		return r.To
	}
	return r.ToCreate
}

// MapShard deterministically maps an address to a shard ID.
// Uses SHA-256 hash modulo the number of shards for uniform distribution.
func MapShard(addr string, shards int) int {
	if shards <= 0 {
		return 0
	}
	
	// Normalize address (remove 0x prefix if present)
	addr = strings.TrimPrefix(strings.ToLower(addr), "0x")
	
	// Hash the address
	hash := sha256.Sum256([]byte(addr))
	
	// Use first 8 bytes of hash as uint64
	hashNum := binary.BigEndian.Uint64(hash[:8])
	
	// Map to shard via modulo
	return int(hashNum % uint64(shards))
}

// MapShardAddress is a helper that works with utils.Address type
func MapShardAddress(addr utils.Address, shards int) int {
	return MapShard(string(addr), shards)
}

// IsCrossShard returns true if the sender and recipient are in different shards
func IsCrossShard(fromAddr, toAddr string, shards int) bool {
	if shards <= 1 {
		return false
	}
	return MapShard(fromAddr, shards) != MapShard(toAddr, shards)
}

