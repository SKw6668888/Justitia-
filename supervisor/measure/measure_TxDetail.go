package measure

import (
	"blockEmulator/message"
	"math/big"
	"strconv"
	"time"
)

type txMetricDetailTime struct {
	// normal tx time
	TxProposeTimestamp, BlockProposeTimestamp, TxCommitTimestamp time.Time

	// relay tx time
	Relay1CommitTimestamp, Relay2CommitTimestamp time.Time

	// broker tx time
	Broker1CommitTimestamp, Broker2CommitTimestamp time.Time

	// fee and transaction info
	FeeToProposer *big.Int
	SubsidyR      *big.Int
	IsCrossShard  bool
	FromShard     int
	ToShard       int
}

// to test Tx detail
type TestTxDetail struct {
	txHash2DetailTime map[string]*txMetricDetailTime
}

func NewTestTxDetail() *TestTxDetail {
	return &TestTxDetail{
		txHash2DetailTime: make(map[string]*txMetricDetailTime),
	}
}

func (ttd *TestTxDetail) OutputMetricName() string {
	return "Tx_Details"
}

func (ttd *TestTxDetail) UpdateMeasureRecord(b *message.BlockInfoMsg) {
	if b.BlockBodyLength == 0 { // empty block
		return
	}

	for _, innertx := range b.InnerShardTxs {
		if _, ok := ttd.txHash2DetailTime[string(innertx.TxHash)]; !ok {
			ttd.txHash2DetailTime[string(innertx.TxHash)] = &txMetricDetailTime{}
		}
		ttd.txHash2DetailTime[string(innertx.TxHash)].TxProposeTimestamp = innertx.Time
		ttd.txHash2DetailTime[string(innertx.TxHash)].BlockProposeTimestamp = b.ProposeTime
		ttd.txHash2DetailTime[string(innertx.TxHash)].TxCommitTimestamp = b.CommitTime
		// Record fee and transaction info
		if innertx.FeeToProposer != nil {
			ttd.txHash2DetailTime[string(innertx.TxHash)].FeeToProposer = new(big.Int).Set(innertx.FeeToProposer)
		}
		if innertx.SubsidyR != nil {
			ttd.txHash2DetailTime[string(innertx.TxHash)].SubsidyR = new(big.Int).Set(innertx.SubsidyR)
		}
		ttd.txHash2DetailTime[string(innertx.TxHash)].IsCrossShard = innertx.IsCrossShard
		ttd.txHash2DetailTime[string(innertx.TxHash)].FromShard = innertx.FromShard
		ttd.txHash2DetailTime[string(innertx.TxHash)].ToShard = innertx.ToShard
	}
	for _, r1tx := range b.Relay1Txs {
		if _, ok := ttd.txHash2DetailTime[string(r1tx.TxHash)]; !ok {
			ttd.txHash2DetailTime[string(r1tx.TxHash)] = &txMetricDetailTime{}
		}
		ttd.txHash2DetailTime[string(r1tx.TxHash)].TxProposeTimestamp = r1tx.Time
		ttd.txHash2DetailTime[string(r1tx.TxHash)].BlockProposeTimestamp = b.ProposeTime
		ttd.txHash2DetailTime[string(r1tx.TxHash)].Relay1CommitTimestamp = b.CommitTime
		// Record fee and transaction info
		if r1tx.FeeToProposer != nil {
			ttd.txHash2DetailTime[string(r1tx.TxHash)].FeeToProposer = new(big.Int).Set(r1tx.FeeToProposer)
		}
		if r1tx.SubsidyR != nil {
			ttd.txHash2DetailTime[string(r1tx.TxHash)].SubsidyR = new(big.Int).Set(r1tx.SubsidyR)
		}
		ttd.txHash2DetailTime[string(r1tx.TxHash)].IsCrossShard = r1tx.IsCrossShard
		ttd.txHash2DetailTime[string(r1tx.TxHash)].FromShard = r1tx.FromShard
		ttd.txHash2DetailTime[string(r1tx.TxHash)].ToShard = r1tx.ToShard
	}
	for _, r2tx := range b.Relay2Txs {
		if _, ok := ttd.txHash2DetailTime[string(r2tx.TxHash)]; !ok {
			ttd.txHash2DetailTime[string(r2tx.TxHash)] = &txMetricDetailTime{}
		}
		ttd.txHash2DetailTime[string(r2tx.TxHash)].Relay2CommitTimestamp = b.CommitTime
		ttd.txHash2DetailTime[string(r2tx.TxHash)].TxCommitTimestamp = b.CommitTime
		// Record fee and transaction info (if not already recorded)
		if r2tx.FeeToProposer != nil && ttd.txHash2DetailTime[string(r2tx.TxHash)].FeeToProposer == nil {
			ttd.txHash2DetailTime[string(r2tx.TxHash)].FeeToProposer = new(big.Int).Set(r2tx.FeeToProposer)
		}
		if r2tx.SubsidyR != nil && ttd.txHash2DetailTime[string(r2tx.TxHash)].SubsidyR == nil {
			ttd.txHash2DetailTime[string(r2tx.TxHash)].SubsidyR = new(big.Int).Set(r2tx.SubsidyR)
		}
		if !ttd.txHash2DetailTime[string(r2tx.TxHash)].IsCrossShard {
			ttd.txHash2DetailTime[string(r2tx.TxHash)].IsCrossShard = r2tx.IsCrossShard
			ttd.txHash2DetailTime[string(r2tx.TxHash)].FromShard = r2tx.FromShard
			ttd.txHash2DetailTime[string(r2tx.TxHash)].ToShard = r2tx.ToShard
		}
	}
	for _, b1tx := range b.Broker1Txs {
		if _, ok := ttd.txHash2DetailTime[string(b1tx.RawTxHash)]; !ok {
			ttd.txHash2DetailTime[string(b1tx.RawTxHash)] = &txMetricDetailTime{}
		}
		ttd.txHash2DetailTime[string(b1tx.RawTxHash)].TxProposeTimestamp = b1tx.Time
		ttd.txHash2DetailTime[string(b1tx.RawTxHash)].BlockProposeTimestamp = b.ProposeTime
		ttd.txHash2DetailTime[string(b1tx.RawTxHash)].Broker1CommitTimestamp = b.CommitTime
		// Record fee and transaction info
		if b1tx.FeeToProposer != nil {
			ttd.txHash2DetailTime[string(b1tx.RawTxHash)].FeeToProposer = new(big.Int).Set(b1tx.FeeToProposer)
		}
		if b1tx.SubsidyR != nil {
			ttd.txHash2DetailTime[string(b1tx.RawTxHash)].SubsidyR = new(big.Int).Set(b1tx.SubsidyR)
		}
		ttd.txHash2DetailTime[string(b1tx.RawTxHash)].IsCrossShard = b1tx.IsCrossShard
		ttd.txHash2DetailTime[string(b1tx.RawTxHash)].FromShard = b1tx.FromShard
		ttd.txHash2DetailTime[string(b1tx.RawTxHash)].ToShard = b1tx.ToShard
	}
	for _, b2tx := range b.Broker2Txs {
		if _, ok := ttd.txHash2DetailTime[string(b2tx.RawTxHash)]; !ok {
			ttd.txHash2DetailTime[string(b2tx.RawTxHash)] = &txMetricDetailTime{}
		}
		ttd.txHash2DetailTime[string(b2tx.RawTxHash)].Broker2CommitTimestamp = b.CommitTime
		ttd.txHash2DetailTime[string(b2tx.RawTxHash)].TxCommitTimestamp = b.CommitTime
		// Record fee and transaction info (if not already recorded)
		if b2tx.FeeToProposer != nil && ttd.txHash2DetailTime[string(b2tx.RawTxHash)].FeeToProposer == nil {
			ttd.txHash2DetailTime[string(b2tx.RawTxHash)].FeeToProposer = new(big.Int).Set(b2tx.FeeToProposer)
		}
		if b2tx.SubsidyR != nil && ttd.txHash2DetailTime[string(b2tx.RawTxHash)].SubsidyR == nil {
			ttd.txHash2DetailTime[string(b2tx.RawTxHash)].SubsidyR = new(big.Int).Set(b2tx.SubsidyR)
		}
		if !ttd.txHash2DetailTime[string(b2tx.RawTxHash)].IsCrossShard {
			ttd.txHash2DetailTime[string(b2tx.RawTxHash)].IsCrossShard = b2tx.IsCrossShard
			ttd.txHash2DetailTime[string(b2tx.RawTxHash)].FromShard = b2tx.FromShard
			ttd.txHash2DetailTime[string(b2tx.RawTxHash)].ToShard = b2tx.ToShard
		}
	}
}

func (ttd *TestTxDetail) HandleExtraMessage([]byte) {}

func (ttd *TestTxDetail) OutputRecord() (perEpochCTXs []float64, totTxNum float64) {
	ttd.writeToCSV()
	return []float64{}, 0
}

func (ttd *TestTxDetail) writeToCSV() {
	fileName := ttd.OutputMetricName()
	measureName := []string{
		"TxHash (Byte -> Big Int)",
		"Tx propose timestamp",
		"Block propose timestamp",
		"Tx finally commit timestamp",
		"Relay1 Tx commit timestamp (not a relay tx -> nil)",
		"Relay2 Tx commit timestamp (not a relay tx -> nil)",
		"Broker1 Tx commit timestamp (not a broker tx -> nil)",
		"Broker2 Tx commit timestamp (not a broker tx -> nil)",
		"Confirmed latency of this tx (ms)",
		"FeeToProposer (wei)",
		"SubsidyR (wei)",
		"IsCrossShard",
		"FromShard",
		"ToShard",
	}
	measureVals := make([][]string, 0)

	for key, val := range ttd.txHash2DetailTime {
		// Calculate confirmed latency with validation
		var confirmedLatency int64
		if !val.TxProposeTimestamp.IsZero() && !val.TxCommitTimestamp.IsZero() &&
			val.TxProposeTimestamp.Before(val.TxCommitTimestamp) &&
			val.TxProposeTimestamp.Year() > 2020 { // Sanity check
			
			confirmedLatency = val.TxCommitTimestamp.Sub(val.TxProposeTimestamp).Milliseconds()
			
			// Additional validation: reject obviously wrong values
			if confirmedLatency < 0 || confirmedLatency > 500000 { // > 500 seconds
				// Skip this transaction with invalid latency
				continue
			}
		} else {
			// Skip transactions with invalid timestamps
			continue
		}
		
		// Format fee to proposer
		feeStr := "0"
		if val.FeeToProposer != nil {
			feeStr = val.FeeToProposer.String()
		}
		
		// Format subsidy
		subsidyStr := "0"
		if val.SubsidyR != nil {
			subsidyStr = val.SubsidyR.String()
		}
		
		csvLine := []string{
			new(big.Int).SetBytes([]byte(key)).String(),

			timestampToString(val.TxProposeTimestamp),
			timestampToString(val.BlockProposeTimestamp),
			timestampToString(val.TxCommitTimestamp),

			timestampToString(val.Relay1CommitTimestamp),
			timestampToString(val.Relay2CommitTimestamp),

			timestampToString(val.Broker1CommitTimestamp),
			timestampToString(val.Broker2CommitTimestamp),

			strconv.FormatInt(confirmedLatency, 10),
			feeStr,
			subsidyStr,
			strconv.FormatBool(val.IsCrossShard),
			strconv.Itoa(val.FromShard),
			strconv.Itoa(val.ToShard),
		}
		measureVals = append(measureVals, csvLine)
	}

	WriteMetricsToCSV(fileName, measureName, measureVals)
}

// zero time to empty string
func timestampToString(thisTime time.Time) string {
	if thisTime.IsZero() {
		return ""
	}
	return strconv.FormatInt(thisTime.UnixMilli(), 10)
}
