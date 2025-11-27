package committee

import (
	"blockEmulator/core"
	"blockEmulator/ingest/ethcsv"
	"blockEmulator/message"
	"blockEmulator/networks"
	"blockEmulator/params"
	"blockEmulator/supervisor/signal"
	"blockEmulator/supervisor/supervisor_log"
	"blockEmulator/utils"
	"encoding/csv"
	"encoding/json"
	"io"
	"log"
	"math/big"
	"os"
	"strconv"
	"time"
)

type RelayCommitteeModule struct {
	csvPath      string
	dataTotalNum int
	nowDataNum   int
	batchDataNum int
	IpNodeTable  map[uint64]map[uint64]string
	sl           *supervisor_log.SupervisorLog
	Ss           *signal.StopSignal // to control the stop message sending
}

func NewRelayCommitteeModule(Ip_nodeTable map[uint64]map[uint64]string, Ss *signal.StopSignal, slog *supervisor_log.SupervisorLog, csvFilePath string, dataNum, batchNum int) *RelayCommitteeModule {
	return &RelayCommitteeModule{
		csvPath:      csvFilePath,
		dataTotalNum: dataNum,
		batchDataNum: batchNum,
		nowDataNum:   0,
		IpNodeTable:  Ip_nodeTable,
		Ss:           Ss,
		sl:           slog,
	}
}

// transfrom, data to transaction
// check whether it is a legal txs meesage. if so, read txs and put it into the txlist
// CSV format: blockNumber,timestamp,transactionHash,from,to,toCreate,fromIsContract,toIsContract,value,gasLimit,gasPrice,gasUsed,callingFunction,isError,eip2718type,baseFeePerGas,maxFeePerGas,maxPriorityFeePerGas,...
func data2tx(data []string, nonce uint64) (*core.Transaction, bool) {
	// Skip header row
	if data[0] == "blockNumber" {
		return &core.Transaction{}, false
	}

	// Check basic validity: not contract creation, valid addresses
	if data[6] == "0" && data[7] == "0" && len(data[3]) > 16 && len(data[4]) > 16 && data[3] != data[4] {
		// Parse value
		val, ok := new(big.Int).SetString(data[8], 10)
		if !ok {
			log.Panic("new int failed\n")
		}

		// Create basic transaction
		tx := core.NewTransaction(data[3][2:], data[4][2:], val, nonce, time.Now())

		// Parse and set fee using ethcsv package for accurate fee computation
		if len(data) >= 12 { // Ensure we have gasPrice field
			// Parse CSV row into ethcsv.TxRow for proper fee calculation
			row := parseCSVRow(data)

			// Compute proposer fee using the ONLY source of truth
			proposerFee := ethcsv.ComputeProposerFee(row)

			// Set the fee (this is the actual fee from the dataset)
			if proposerFee != nil && proposerFee.Sign() > 0 {
				tx.FeeToProposer = proposerFee
			} else {
				// Fallback to default if fee computation failed
				tx.FeeToProposer = big.NewInt(1_000_000_000) // 1 Gwei
			}
		} else {
			// Old CSV format without gas fields, use default
			tx.FeeToProposer = big.NewInt(1_000_000_000) // 1 Gwei
		}

		return tx, true
	}
	return &core.Transaction{}, false
}

// parseCSVRow converts CSV string array to ethcsv.TxRow for fee computation
func parseCSVRow(data []string) ethcsv.TxRow {
	row := ethcsv.TxRow{}

	// Parse basic fields
	if len(data) > 0 {
		if bn, err := strconv.ParseUint(data[0], 10, 64); err == nil {
			row.BlockNumber = bn
		}
	}
	if len(data) > 2 {
		row.TxHash = data[2]
	}
	if len(data) > 3 {
		row.From = data[3]
	}
	if len(data) > 4 {
		row.To = data[4]
	}
	if len(data) > 8 {
		if val, ok := new(big.Int).SetString(data[8], 10); ok {
			row.Value = val
		}
	}

	// Parse gas fields (critical for fee computation)
	if len(data) > 9 {
		if gl, err := strconv.ParseUint(data[9], 10, 64); err == nil {
			row.GasLimit = gl
		}
	}
	if len(data) > 10 && data[10] != "" && data[10] != "None" {
		if gp, ok := new(big.Int).SetString(data[10], 10); ok {
			row.GasPrice = gp
		}
	}
	if len(data) > 11 {
		if gu, err := strconv.ParseUint(data[11], 10, 64); err == nil {
			row.GasUsed = gu
		}
	}

	// Parse EIP-2718 type (0=legacy, 2=EIP-1559, etc.)
	if len(data) > 14 && data[14] != "" && data[14] != "None" {
		if eipType, err := strconv.ParseUint(data[14], 10, 8); err == nil {
			row.EIP2718Type = uint8(eipType)
		}
	}

	// Parse EIP-1559 fields (for type 2 transactions)
	if len(data) > 15 && data[15] != "" && data[15] != "None" {
		if baseFee, ok := new(big.Int).SetString(data[15], 10); ok {
			row.BaseFeePerGas = baseFee
		}
	}
	if len(data) > 16 && data[16] != "" && data[16] != "None" {
		if maxFee, ok := new(big.Int).SetString(data[16], 10); ok {
			row.MaxFeePerGas = maxFee
		}
	}
	if len(data) > 17 && data[17] != "" && data[17] != "None" {
		if maxPriority, ok := new(big.Int).SetString(data[17], 10); ok {
			row.MaxPriorityFeePerGas = maxPriority
		}
	}

	return row
}

func (rthm *RelayCommitteeModule) HandleOtherMessage([]byte) {}

func (rthm *RelayCommitteeModule) txSending(txlist []*core.Transaction) {
	// the txs will be sent
	sendToShard := make(map[uint64][]*core.Transaction)

	for idx := 0; idx <= len(txlist); idx++ {
		if idx > 0 && (idx%params.InjectSpeed == 0 || idx == len(txlist)) {
			// send to shard
			for sid := uint64(0); sid < uint64(params.ShardNum); sid++ {
				it := message.InjectTxs{
					Txs:       sendToShard[sid],
					ToShardID: sid,
				}
				itByte, err := json.Marshal(it)
				if err != nil {
					log.Panic(err)
				}
				send_msg := message.MergeMessage(message.CInject, itByte)
				go networks.TcpDial(send_msg, rthm.IpNodeTable[sid][0])
			}
			sendToShard = make(map[uint64][]*core.Transaction)
			time.Sleep(time.Second)
		}
		if idx == len(txlist) {
			break
		}
		tx := txlist[idx]
		sendersid := uint64(utils.Addr2Shard(tx.Sender))
		recipientsid := uint64(utils.Addr2Shard(tx.Recipient))

		// Justitia: Set shard information for cross-shard transaction detection
		tx.FromShard = int(sendersid)
		tx.ToShard = int(recipientsid)
		tx.IsCrossShard = (sendersid != recipientsid)
		tx.PairID = string(tx.TxHash)

		// Set fee (default if not already set from CSV)
		if tx.FeeToProposer == nil || tx.FeeToProposer.Sign() == 0 {
			// Default fee: 1 Gwei (reasonable for Ethereum transactions)
			tx.FeeToProposer = big.NewInt(1_000_000_000) // 1 Gwei
		}

		// Set arrival time for latency tracking
		if tx.ArrivalTime.IsZero() {
			tx.ArrivalTime = time.Now()
		}

		sendToShard[sendersid] = append(sendToShard[sendersid], tx)
	}
}

// read transactions, the Number of the transactions is - batchDataNum
func (rthm *RelayCommitteeModule) MsgSendingControl() {
	txfile, err := os.Open(rthm.csvPath)
	if err != nil {
		log.Panic(err)
	}
	defer txfile.Close()
	reader := csv.NewReader(txfile)
	txlist := make([]*core.Transaction, 0) // save the txs in this epoch (round)

	for {
		data, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Panic(err)
		}
		if tx, ok := data2tx(data, uint64(rthm.nowDataNum)); ok {
			txlist = append(txlist, tx)
			rthm.nowDataNum++
		}

		// re-shard condition, enough edges
		if len(txlist) == int(rthm.batchDataNum) || rthm.nowDataNum == rthm.dataTotalNum {
			rthm.txSending(txlist)
			// reset the variants about tx sending
			txlist = make([]*core.Transaction, 0)
			rthm.Ss.StopGap_Reset()
		}

		if rthm.nowDataNum == rthm.dataTotalNum {
			break
		}
	}
}

// no operation here
func (rthm *RelayCommitteeModule) HandleBlockInfo(b *message.BlockInfoMsg) {
	rthm.sl.Slog.Printf("received from shard %d in epoch %d.\n", b.SenderShardID, b.Epoch)
}
