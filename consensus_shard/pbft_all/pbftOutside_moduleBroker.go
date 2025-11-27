package pbft_all

import (
	"blockEmulator/fees"
	"blockEmulator/message"
	"encoding/json"
	"log"
)

// This module used in the blockChain using transaction relaying mechanism.
// "Raw" means that the pbft only make block consensus.
type RawBrokerOutsideModule struct {
	pbftNode *PbftConsensusNode
}

// msgType canbe defined in message
func (rrom *RawBrokerOutsideModule) HandleMessageOutsidePBFT(msgType message.MessageType, content []byte) bool {
	switch msgType {
	case message.CSeqIDinfo:
		rrom.handleSeqIDinfos(content)
	case message.CInject:
		rrom.handleInjectTx(content)
	case message.CFeeInfoSync:
		rrom.handleFeeInfoSync(content)
	default:
	}
	return true
}

// receive SeqIDinfo
func (rrom *RawBrokerOutsideModule) handleSeqIDinfos(content []byte) {
	sii := new(message.SeqIDinfo)
	err := json.Unmarshal(content, sii)
	if err != nil {
		log.Panic(err)
	}
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has received SeqIDinfo from shard %d, the senderSeq is %d\n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, sii.SenderShardID, sii.SenderSeq)
	rrom.pbftNode.seqMapLock.Lock()
	rrom.pbftNode.seqIDMap[sii.SenderShardID] = sii.SenderSeq
	rrom.pbftNode.seqMapLock.Unlock()
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has handled SeqIDinfo msg\n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID)
}

func (rrom *RawBrokerOutsideModule) handleInjectTx(content []byte) {
	it := new(message.InjectTxs)
	err := json.Unmarshal(content, it)
	if err != nil {
		log.Panic(err)
	}
	rrom.pbftNode.CurChain.Txpool.AddTxs2Pool(it.Txs)
	rrom.pbftNode.pl.Plog.Printf("S%dN%d : has handled injected txs msg, txs: %d \n", rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, len(it.Txs))
}

// handleFeeInfoSync processes fee synchronization messages from other shards
func (rrom *RawBrokerOutsideModule) handleFeeInfoSync(content []byte) {
	feeMsg := new(message.FeeInfoSync)
	err := json.Unmarshal(content, feeMsg)
	if err != nil {
		rrom.pbftNode.pl.Plog.Printf("S%dN%d : Error unmarshaling fee info: %v\n",
			rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, err)
		return
	}

	feeTracker := fees.GetGlobalTracker()
	feeTracker.UpdateRemoteShardFee(int(feeMsg.ShardID), feeMsg.AvgITXFee)

	rrom.pbftNode.pl.Plog.Printf("S%dN%d : Received fee info from S%d: E(f_%d)=%s at block %d\n",
		rrom.pbftNode.ShardID, rrom.pbftNode.NodeID, feeMsg.ShardID,
		feeMsg.ShardID, feeMsg.AvgITXFee.String(), feeMsg.BlockHeight)
}
