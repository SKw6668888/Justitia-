// Definition of transaction

package core

import (
	"blockEmulator/utils"
	"bytes"
	"crypto/sha256"
	"encoding/gob"
	"fmt"
	"log"
	"math/big"
	"time"
)

type Transaction struct {
	Sender    utils.Address
	Recipient utils.Address
	Nonce     uint64
	Signature []byte // not implemented now.
	Value     *big.Int
	TxHash    []byte

	Time time.Time // TimeStamp the tx proposed.

	// used in transaction relaying
	Relayed bool
	// used in broker, if the tx is not a broker1 or broker2 tx, these values should be empty.
	HasBroker      bool
	SenderIsBroker bool
	OriginalSender utils.Address
	FinalRecipient utils.Address
	RawTxHash      []byte

	// Justitia incentive mechanism fields
	FromShard        int       // Source shard ID (computed from sender address)
	ToShard          int       // Destination shard ID (computed from recipient address)
	IsCrossShard     bool      // Whether this is a cross-shard transaction
	PairID           string    // Unique identifier for matching CTX and CTX' (typically TxHash as string)
	FeeToProposer    *big.Int  // Fee that goes to proposer (f_AB for CTX, f for ITX)
	ArrivalTime      time.Time // Time when tx arrived at mempool (for delay metrics)
	TxSize           int       // Transaction size (default 1 for count-based capacity)
	
	// Cross-shard reward tracking
	SubsidyR         *big.Int  // Subsidy R_AB for this CTX
	UtilityA         *big.Int  // Utility uA for source shard proposer
	UtilityB         *big.Int  // Utility uB for destination shard proposer
	JustitiaCase     int       // Classification: 1=Case1, 2=Case2, 3=Case3 (0=not classified/ITX)
	
	// Relay tracking
	IsRelay2         bool      // Whether this is the second phase of relay (executed in recipient shard)
	OriginalPropTime time.Time // Original proposal time (for relay2 txs to track end-to-end latency)
	IncludedInBlockA uint64    // Block number where CTX was included in source shard A
	IncludedInBlockB uint64    // Block number where CTX' was included in dest shard B
}

func (tx *Transaction) PrintTx() string {
	vals := []interface{}{
		tx.Sender[:],
		tx.Recipient[:],
		tx.Value,
		string(tx.TxHash[:]),
	}
	res := fmt.Sprintf("%v\n", vals)
	return res
}

// Encode transaction for storing
func (tx *Transaction) Encode() []byte {
	var buff bytes.Buffer

	enc := gob.NewEncoder(&buff)
	err := enc.Encode(tx)
	if err != nil {
		log.Panic(err)
	}

	return buff.Bytes()
}

// Decode transaction
func DecodeTx(to_decode []byte) *Transaction {
	var tx Transaction

	decoder := gob.NewDecoder(bytes.NewReader(to_decode))
	err := decoder.Decode(&tx)
	if err != nil {
		log.Panic(err)
	}

	return &tx
}

// new a transaction
func NewTransaction(sender, recipient string, value *big.Int, nonce uint64, proposeTime time.Time) *Transaction {
	tx := &Transaction{
		Sender:    sender,
		Recipient: recipient,
		Value:     value,
		Nonce:     nonce,
		Time:      proposeTime,
	}

	hash := sha256.Sum256(tx.Encode())
	tx.TxHash = hash[:]
	tx.Relayed = false
	tx.FinalRecipient = ""
	tx.OriginalSender = ""
	tx.RawTxHash = nil
	tx.HasBroker = false
	tx.SenderIsBroker = false
	
	// Initialize Justitia fields
	tx.FromShard = 0
	tx.ToShard = 0
	tx.IsCrossShard = false
	tx.PairID = ""
	tx.FeeToProposer = big.NewInt(0)
	tx.ArrivalTime = proposeTime
	tx.TxSize = 1 // Default size = 1 for count-based capacity
	
	tx.SubsidyR = big.NewInt(0)
	tx.UtilityA = big.NewInt(0)
	tx.UtilityB = big.NewInt(0)
	tx.JustitiaCase = 0
	
	tx.IsRelay2 = false
	tx.OriginalPropTime = proposeTime
	tx.IncludedInBlockA = 0
	tx.IncludedInBlockB = 0
	
	return tx
}
