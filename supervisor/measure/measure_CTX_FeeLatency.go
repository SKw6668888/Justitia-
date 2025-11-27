package measure

import (
	"blockEmulator/message"
	"math/big"
	"strconv"
	"time"
)

// CTXFeeLatencyMetric stores fee and latency information for a CTX
type CTXFeeLatencyMetric struct {
	TxHash          string
	FeeToProposer   *big.Int // Fee paid to proposer (f_AB)
	ArrivalTime     time.Time // When tx arrived at mempool
	QueueLatency    int64     // Queue latency in milliseconds (from arrival to commit)
	CommitTime      time.Time // When tx was committed
	IsRelay2        bool      // Whether this is relay2 (final commit)
	OriginalPropTime time.Time // Original proposal time for end-to-end latency
}

// TestModule_CTX_FeeLatency measures fee quantile vs queue latency for CTX
type TestModule_CTX_FeeLatency struct {
	ctxMetrics []*CTXFeeLatencyMetric // Store all CTX metrics
	relay1CommitTS map[string]time.Time // Track relay1 commit times for matching
}

func NewTestModule_CTX_FeeLatency() *TestModule_CTX_FeeLatency {
	return &TestModule_CTX_FeeLatency{
		ctxMetrics:     make([]*CTXFeeLatencyMetric, 0),
		relay1CommitTS: make(map[string]time.Time),
	}
}

func (tmcfl *TestModule_CTX_FeeLatency) OutputMetricName() string {
	return "CTX_Fee_Latency"
}

func (tmcfl *TestModule_CTX_FeeLatency) UpdateMeasureRecord(b *message.BlockInfoMsg) {
	if b.BlockBodyLength == 0 { // empty block
		return
	}

	// Process relay1 transactions (first phase of CTX)
	for _, r1tx := range b.Relay1Txs {
		tmcfl.relay1CommitTS[string(r1tx.TxHash)] = b.CommitTime
	}

	// Process relay2 transactions (second phase of CTX - final commit)
	// This is where we measure the complete queue latency for CTX
	for _, r2tx := range b.Relay2Txs {
		// Calculate queue latency: from arrival time to commit time
		var queueLatency int64
		var validLatency bool
		
		// Use ArrivalTime if available (most accurate)
		if !r2tx.ArrivalTime.IsZero() && r2tx.ArrivalTime.Before(b.CommitTime) {
			queueLatency = b.CommitTime.Sub(r2tx.ArrivalTime).Milliseconds()
			// Validate: should be positive and reasonable (< 500 seconds)
			if queueLatency > 0 && queueLatency < 500000 {
				validLatency = true
			}
		}
		
		// Fallback: use OriginalPropTime if ArrivalTime is not available
		if !validLatency && !r2tx.OriginalPropTime.IsZero() && 
		   r2tx.OriginalPropTime.Before(b.CommitTime) &&
		   r2tx.OriginalPropTime.Year() > 2020 {
			queueLatency = b.CommitTime.Sub(r2tx.OriginalPropTime).Milliseconds()
			if queueLatency > 0 && queueLatency < 500000 {
				validLatency = true
			}
		}
		
		// Last resort: use Time field (proposal time)
		if !validLatency && !r2tx.Time.IsZero() && r2tx.Time.Before(b.CommitTime) {
			queueLatency = b.CommitTime.Sub(r2tx.Time).Milliseconds()
			if queueLatency > 0 && queueLatency < 500000 {
				validLatency = true
			}
		}
		
		// Skip if we can't calculate valid latency
		if !validLatency {
			continue
		}
		
		// Get fee (should not be nil, but handle gracefully)
		fee := r2tx.FeeToProposer
		if fee == nil {
			fee = big.NewInt(0)
		}
		
		// Create metric record
		metric := &CTXFeeLatencyMetric{
			TxHash:          new(big.Int).SetBytes(r2tx.TxHash).String(),
			FeeToProposer:   new(big.Int).Set(fee),
			ArrivalTime:     r2tx.ArrivalTime,
			QueueLatency:    queueLatency,
			CommitTime:      b.CommitTime,
			IsRelay2:        true,
			OriginalPropTime: r2tx.OriginalPropTime,
		}
		
		tmcfl.ctxMetrics = append(tmcfl.ctxMetrics, metric)
	}
}

func (tmcfl *TestModule_CTX_FeeLatency) HandleExtraMessage([]byte) {}

func (tmcfl *TestModule_CTX_FeeLatency) OutputRecord() ([]float64, float64) {
	tmcfl.writeToCSV()
	return []float64{}, 0
}

func (tmcfl *TestModule_CTX_FeeLatency) writeToCSV() {
	fileName := tmcfl.OutputMetricName()
	measureName := []string{
		"TxHash",
		"FeeToProposer (wei)",
		"ArrivalTime (ms)",
		"CommitTime (ms)",
		"QueueLatency (ms)",
		"OriginalPropTime (ms)",
	}
	
	measureVals := make([][]string, 0)
	for _, metric := range tmcfl.ctxMetrics {
		csvLine := []string{
			metric.TxHash,
			metric.FeeToProposer.String(),
			timestampToStringMs(metric.ArrivalTime),
			timestampToStringMs(metric.CommitTime),
			strconv.FormatInt(metric.QueueLatency, 10),
			timestampToStringMs(metric.OriginalPropTime),
		}
		measureVals = append(measureVals, csvLine)
	}
	
	WriteMetricsToCSV(fileName, measureName, measureVals)
}

// timestampToStringMs converts time to string (milliseconds since epoch)
func timestampToStringMs(thisTime time.Time) string {
	if thisTime.IsZero() {
		return ""
	}
	return strconv.FormatInt(thisTime.UnixMilli(), 10)
}

