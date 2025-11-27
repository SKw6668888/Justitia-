package pbft_all

import (
	"blockEmulator/chain"
	"blockEmulator/fees"
	"blockEmulator/message"
	"blockEmulator/params"
	"encoding/json"
	"log"
)

// This module used in the blockChain using transaction relaying mechanism.
// "Raw" means that the pbft only make block consensus.
type RawRelayOutsideModule struct {
	pbftNode *PbftConsensusNode
}

// msgType canbe defined in message
func (rrom *RawRelayOutsideModule) HandleMessageOutsidePBFT(msgType message.MessageType, content []byte) bool {
	switch msgType {
	case message.CRelay:
		rrom.handleRelay(content)
	case message.CRelayWithProof:
		rrom.handleRelayWithProof(content)
	case message.CInject:
		rrom.handleInjectTx(content)
	case message.CFeeInfoSync:
		rrom.handleFeeInfoSync(content)
	default:
	}
	return true
}

// receive relay transaction, which is for cross shard txs
func (rrom *RawRelayOutsideModule) handleRelay(content []byte) {
	relay := new(message.Relay)
	err := json.Unmarshal(content, relay)
	if err != nil {
		log.Panic(err)
	}
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has received relay txs from shard %d, the senderSeq is %d\n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, relay.SenderShardID, relay.SenderSeq)

	// Justitia: mark relay2 transactions for priority processing
	for _, tx := range relay.Txs {
		if params.EnableJustitia == 1 && tx.IsCrossShard {
			tx.IsRelay2 = true
			// Keep the original proposal time and Justitia reward
			// These should have been set in the source shard
		}
	}

	rrom.pbftNode.CurChain.Txpool.AddTxs2Pool(relay.Txs)
	rrom.pbftNode.seqMapLock.Lock()
	rrom.pbftNode.seqIDMap[relay.SenderShardID] = relay.SenderSeq
	rrom.pbftNode.seqMapLock.Unlock()
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has handled relay txs msg\n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID)
}

func (rrom *RawRelayOutsideModule) handleRelayWithProof(content []byte) {
	rwp := new(message.RelayWithProof)
	err := json.Unmarshal(content, rwp)
	if err != nil {
		log.Panic(err)
	}
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has received relay txs & proofs from shard %d, the senderSeq is %d\n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, rwp.SenderShardID, rwp.SenderSeq)
	// validate the proofs of txs
	isAllCorrect := true
	for i, tx := range rwp.Txs {
		if ok, _ := chain.TxProofVerify(tx.TxHash, &rwp.TxProofs[i]); !ok {
			isAllCorrect = false
			break
		}
	}
	if isAllCorrect {
		rrom.pbftNode.pl.Plog.Println("All proofs are passed.")
		rrom.pbftNode.CurChain.Txpool.AddTxs2Pool(rwp.Txs)
	} else {
		rrom.pbftNode.pl.Plog.Println("Err: wrong proof!")
	}

	rrom.pbftNode.seqMapLock.Lock()
	rrom.pbftNode.seqIDMap[rwp.SenderShardID] = rwp.SenderSeq
	rrom.pbftNode.seqMapLock.Unlock()
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has handled relay txs msg\n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID)
}

func (rrom *RawRelayOutsideModule) handleInjectTx(content []byte) {
	it := new(message.InjectTxs)
	err := json.Unmarshal(content, it)
	if err != nil {
		log.Panic(err)
	}
	rrom.pbftNode.CurChain.Txpool.AddTxs2Pool(it.Txs)
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has handled injected txs msg, txs: %d \n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, len(it.Txs))
}

// handleFeeInfoSync processes fee synchronization messages from other shards
// This enables cross-shard subsidy calculation in multi-process architecture
func (rrom *RawRelayOutsideModule) handleFeeInfoSync(content []byte) {
	feeMsg := new(message.FeeInfoSync)
	err := json.Unmarshal(content, feeMsg)
	if err != nil {
		rrom.pbftNode.pl.Plog.Printf("S%dN%d : Error unmarshaling fee info: %v\n",
			rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, err)
		return
	}

	// Update the global fee tracker with remote shard's fee info
	feeTracker := fees.GetGlobalTracker()
	feeTracker.UpdateRemoteShardFee(int(feeMsg.ShardID), feeMsg.AvgITXFee)

	rrom.pbftNode.pl.Plog.Printf("S%dN%d : Received fee info from S%d: E(f_%d)=%s at block %d\n",
		rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, feeMsg.ShardID,
		feeMsg.ShardID, feeMsg.AvgITXFee.String(), feeMsg.BlockHeight)
}
