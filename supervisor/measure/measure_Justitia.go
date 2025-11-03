package measure

import (
	"blockEmulator/message"
	"blockEmulator/params"
	"strconv"
	"time"
)

// TestModule_Justitia measures the effectiveness of Justitia incentive mechanism
// It tracks latency differences between cross-shard transactions (CTX) and inner-shard transactions
type TestModule_Justitia struct {
	epochID int

	// Cross-shard transaction metrics
	ctxCount           []int     // count of cross-shard transactions per epoch
	ctxTotalLatency    []float64 // total latency of CTX per epoch (in seconds)
	ctxAvgLatency      []float64 // average latency of CTX per epoch
	ctxRelay1Latency   []int64   // sum of relay1 phase latency (ms)
	ctxRelay2Latency   []int64   // sum of relay2 phase latency (ms)
	ctxEndToEndLatency []int64   // sum of end-to-end latency from original proposal to relay2 commit (ms)

	// Inner-shard transaction metrics
	innerTxCount        []int     // count of inner-shard transactions per epoch
	innerTxTotalLatency []float64 // total latency of inner-shard txs per epoch (in seconds)
	innerTxAvgLatency   []float64 // average latency of inner-shard txs per epoch
	innerTxLatency      []int64   // sum of inner-shard tx latency (ms)

	// Justitia effectiveness metrics
	latencyReduction []float64 // CTX latency reduction compared to inner-shard (negative if CTX is faster)
	priorityRate     []float64 // percentage of CTX in each block (priority effectiveness)

	// Track relay1 commit times for matching with relay2
	relay1CommitTS map[string]time.Time
}

func NewTestModule_Justitia() *TestModule_Justitia {
	return &TestModule_Justitia{
		epochID:            -1,
		ctxCount:           make([]int, 0),
		ctxTotalLatency:    make([]float64, 0),
		ctxAvgLatency:      make([]float64, 0),
		ctxRelay1Latency:   make([]int64, 0),
		ctxRelay2Latency:   make([]int64, 0),
		ctxEndToEndLatency: make([]int64, 0),

		innerTxCount:        make([]int, 0),
		innerTxTotalLatency: make([]float64, 0),
		innerTxAvgLatency:   make([]float64, 0),
		innerTxLatency:      make([]int64, 0),

		latencyReduction: make([]float64, 0),
		priorityRate:     make([]float64, 0),

		relay1CommitTS: make(map[string]time.Time),
	}
}

func (tmj *TestModule_Justitia) OutputMetricName() string {
	return "Justitia_Effectiveness"
}

func (tmj *TestModule_Justitia) UpdateMeasureRecord(b *message.BlockInfoMsg) {
	if b.BlockBodyLength == 0 { // empty block
		return
	}

	epochid := b.Epoch

	// Extend slices if needed
	for tmj.epochID < epochid {
		tmj.ctxCount = append(tmj.ctxCount, 0)
		tmj.ctxTotalLatency = append(tmj.ctxTotalLatency, 0)
		tmj.ctxAvgLatency = append(tmj.ctxAvgLatency, 0)
		tmj.ctxRelay1Latency = append(tmj.ctxRelay1Latency, 0)
		tmj.ctxRelay2Latency = append(tmj.ctxRelay2Latency, 0)
		tmj.ctxEndToEndLatency = append(tmj.ctxEndToEndLatency, 0)

		tmj.innerTxCount = append(tmj.innerTxCount, 0)
		tmj.innerTxTotalLatency = append(tmj.innerTxTotalLatency, 0)
		tmj.innerTxAvgLatency = append(tmj.innerTxAvgLatency, 0)
		tmj.innerTxLatency = append(tmj.innerTxLatency, 0)

		tmj.latencyReduction = append(tmj.latencyReduction, 0)
		tmj.priorityRate = append(tmj.priorityRate, 0)

		tmj.epochID++
	}

	// Process inner-shard transactions
	for _, tx := range b.InnerShardTxs {
		tmj.innerTxCount[epochid]++
		latencySec := b.CommitTime.Sub(tx.Time).Seconds()
		latencyMs := b.CommitTime.Sub(tx.Time).Milliseconds()
		tmj.innerTxTotalLatency[epochid] += latencySec
		tmj.innerTxLatency[epochid] += latencyMs
	}

	// Process relay1 transactions (first phase of CTX)
	for _, r1tx := range b.Relay1Txs {
		tmj.relay1CommitTS[string(r1tx.TxHash)] = b.CommitTime
		relay1Latency := b.CommitTime.Sub(r1tx.Time).Milliseconds()
		tmj.ctxRelay1Latency[epochid] += relay1Latency
	}

	// Process relay2 transactions (second phase of CTX - final commit)
	for _, r2tx := range b.Relay2Txs {
		// Calculate relay2 phase latency first (always valid)
		relay2Latency := b.CommitTime.Sub(r2tx.Time).Milliseconds()
		
		// Skip this transaction if relay2 time itself is invalid
		if relay2Latency < 0 || relay2Latency > 500000 { // > 500 seconds is invalid
			continue // Skip this transaction entirely
		}
		
		tmj.ctxCount[epochid]++
		tmj.ctxRelay2Latency[epochid] += relay2Latency
		
		// Calculate end-to-end latency with strict validation
		var endToEndLatency int64
		validLatency := false
		
		// Method 1: Use OriginalPropTime if available and valid
		if !r2tx.OriginalPropTime.IsZero() && 
		   r2tx.OriginalPropTime.Before(b.CommitTime) &&
		   r2tx.OriginalPropTime.Year() > 2020 { // Sanity check: after 2020
			endToEndLatency = b.CommitTime.Sub(r2tx.OriginalPropTime).Milliseconds()
			// Validate: should be between relay2Latency and 500 seconds
			if endToEndLatency >= relay2Latency && endToEndLatency <= 500000 {
				validLatency = true
			}
		}
		
		// Method 2: Fallback to relay1 commit time
		if !validLatency {
			if r1CommitTime, ok := tmj.relay1CommitTS[string(r2tx.TxHash)]; ok {
				relay1Latency := r1CommitTime.Sub(r2tx.Time).Milliseconds()
				if relay1Latency > 0 && relay1Latency < 500000 {
					endToEndLatency = b.CommitTime.Sub(r1CommitTime).Milliseconds() + relay1Latency
					if endToEndLatency > 0 && endToEndLatency <= 500000 {
						validLatency = true
					}
				}
			}
		}
		
		// Method 3: Last resort - use relay2 latency only (conservative estimate)
		if !validLatency {
			endToEndLatency = relay2Latency
		}
		
		tmj.ctxEndToEndLatency[epochid] += endToEndLatency
		tmj.ctxTotalLatency[epochid] += float64(endToEndLatency) / 1000.0 // convert to seconds
	}

	// Calculate average latencies and effectiveness metrics
	if tmj.ctxCount[epochid] > 0 {
		tmj.ctxAvgLatency[epochid] = tmj.ctxTotalLatency[epochid] / float64(tmj.ctxCount[epochid])
	}

	if tmj.innerTxCount[epochid] > 0 {
		tmj.innerTxAvgLatency[epochid] = tmj.innerTxTotalLatency[epochid] / float64(tmj.innerTxCount[epochid])
	}

	// Calculate latency reduction: (CTX_latency - InnerTx_latency) / InnerTx_latency * 100
	// Negative value means CTX is faster (which is the goal of Justitia)
	if tmj.innerTxAvgLatency[epochid] > 0 && tmj.ctxAvgLatency[epochid] > 0 {
		tmj.latencyReduction[epochid] = ((tmj.ctxAvgLatency[epochid] - tmj.innerTxAvgLatency[epochid]) /
			tmj.innerTxAvgLatency[epochid]) * 100.0
	}

	// Calculate priority rate: percentage of CTX in block
	totalTxs := tmj.ctxCount[epochid] + tmj.innerTxCount[epochid]
	if totalTxs > 0 {
		tmj.priorityRate[epochid] = float64(tmj.ctxCount[epochid]) / float64(totalTxs) * 100.0
	}
}

func (tmj *TestModule_Justitia) HandleExtraMessage(msg []byte) {}

func (tmj *TestModule_Justitia) OutputRecord() (perEpochLatency []float64, totLatency float64) {
	tmj.writeToCSV()

	// Calculate overall metrics
	perEpochLatency = make([]float64, 0)
	totalCtxLatency := 0.0
	totalInnerLatency := 0.0
	totalCtxCount := 0
	totalInnerCount := 0

	for eid := range tmj.ctxAvgLatency {
		// Return the latency reduction per epoch for analysis
		perEpochLatency = append(perEpochLatency, tmj.latencyReduction[eid])

		totalCtxLatency += tmj.ctxTotalLatency[eid]
		totalCtxCount += tmj.ctxCount[eid]
		totalInnerLatency += tmj.innerTxTotalLatency[eid]
		totalInnerCount += tmj.innerTxCount[eid]
	}

	// Overall latency (weighted average of both types)
	if totalCtxCount+totalInnerCount > 0 {
		totLatency = (totalCtxLatency + totalInnerLatency) / float64(totalCtxCount+totalInnerCount)
	}

	return
}

func (tmj *TestModule_Justitia) writeToCSV() {
	if params.EnableJustitia != 1 {
		return // Only write CSV if Justitia is enabled
	}

	fileName := tmj.OutputMetricName()
	measureName := []string{
		"EpochID",
		"Inner-Shard Tx Count",
		"Cross-Shard Tx Count",
		"Inner-Shard Avg Latency (sec)",
		"CTX Avg Latency (sec)",
		"CTX Relay1 Phase Latency (ms)",
		"CTX Relay2 Phase Latency (ms)",
		"CTX End-to-End Latency (ms)",
		"Latency Reduction (%)",
		"CTX Priority Rate (%)",
		"Justitia Reward",
		"Justitia Status",
	}

	measureVals := make([][]string, 0)
	for eid := range tmj.ctxAvgLatency {
		justitiaStatus := "Disabled"
		if params.EnableJustitia == 1 {
			if tmj.latencyReduction[eid] < 0 {
				justitiaStatus = "Effective (CTX faster)"
			} else {
				justitiaStatus = "Ineffective (CTX slower)"
			}
		}

		csvLine := []string{
			strconv.Itoa(eid),
			strconv.Itoa(tmj.innerTxCount[eid]),
			strconv.Itoa(tmj.ctxCount[eid]),
			strconv.FormatFloat(tmj.innerTxAvgLatency[eid], 'f', 6, 64),
			strconv.FormatFloat(tmj.ctxAvgLatency[eid], 'f', 6, 64),
			strconv.FormatInt(tmj.ctxRelay1Latency[eid], 10),
			strconv.FormatInt(tmj.ctxRelay2Latency[eid], 10),
			strconv.FormatInt(tmj.ctxEndToEndLatency[eid], 10),
			strconv.FormatFloat(tmj.latencyReduction[eid], 'f', 2, 64),
			strconv.FormatFloat(tmj.priorityRate[eid], 'f', 2, 64),
			strconv.FormatFloat(params.JustitiaRewardBase, 'f', 2, 64),
			justitiaStatus,
		}
		measureVals = append(measureVals, csvLine)
	}

	WriteMetricsToCSV(fileName, measureName, measureVals)
}
