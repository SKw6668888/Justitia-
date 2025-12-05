package params

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
)

var (
	// The following parameters can be set in main.go.
	// default values:
	NodesInShard = 4 // \# of Nodes in a shard.
	ShardNum     = 4 // \# of shards.
)

// consensus layer & output file path
var (
	ConsensusMethod = 0 // ConsensusMethod an Integer, which indicates the choice ID of methods / consensuses. Value range: [0, 4), representing [CLPA_Broker, CLPA, Broker, Relay]"

	PbftViewChangeTimeOut = 10000 // The view change threshold of pbft. If the process of PBFT is too slow, the view change mechanism will be triggered.

	Block_Interval = 5000 // The time interval for generating a new block

	MaxBlockSize_global = 2000  // The maximum number of transactions a block contains
	BlocksizeInBytes    = 20000 // The maximum size (in bytes) of block body
	UseBlocksizeInBytes = 0     // Use blocksizeInBytes as the blocksize measurement if '1'.

	InjectSpeed   = 2000   // The speed of transaction injection
	TotalDataSize = 160000 // The total number of txs to be injected
	TxBatchSize   = 16000  // The supervisor read a batch of txs then send them. The size of a batch is 'TxBatchSize'

	BrokerNum            = 10 // The # of Broker accounts used in Broker / CLPA_Broker.
	RelayWithMerkleProof = 0  // When using a consensus about "Relay", nodes will send Tx Relay with proof if "RelayWithMerkleProof" = 1

	ExpDataRootDir     = "expTest"                     // The root dir where the experimental data should locate.
	DataWrite_path     = ExpDataRootDir + "/result/"   // Measurement data result output path
	LogWrite_path      = ExpDataRootDir + "/log"       // Log output path
	DatabaseWrite_path = ExpDataRootDir + "/database/" // database write path

	SupervisorAddr = "127.0.0.1:18800"        // Supervisor ip address
	DatasetFile    = `./selectedTxs_300K.csv` // The raw BlockTransaction data path

	ReconfigTimeGap = 50 // The time gap between epochs. This variable is only used in CLPA / CLPA_Broker now.

	// Justitia incentive mechanism parameters
	EnableJustitia       = 0            // Enable Justitia incentive mechanism (1: enabled, 0: disabled)
	JustitiaSubsidyMode  = 1            // Subsidy mode: 0=None, 1=DestAvg, 2=SumAvg, 3=Custom, 4=ExtremeFixed, 5=PID, 6=Lagrangian, 7=RL
	JustitiaWindowBlocks = 16           // Number of blocks for rolling average E(f_s)
	JustitiaGammaMin     = uint64(0)    // Minimum subsidy budget per block (0=no limit)
	JustitiaGammaMax     = uint64(0)    // Maximum subsidy budget per block (0=no limit)
	JustitiaRewardBase   = 100.0        // Legacy: Base reward R (deprecated, use mode instead)
	
	// PID Controller parameters (mode=5)
	JustitiaPID_Kp                = 1.5    // PID proportional gain
	JustitiaPID_Ki                = 0.1    // PID integral gain
	JustitiaPID_Kd                = 0.05   // PID derivative gain
	JustitiaPID_TargetUtilization = 0.7    // Target queue utilization (0.0-1.0)
	JustitiaPID_CapacityB         = 1000.0 // Queue capacity for destination shard
	JustitiaPID_MinSubsidy        = 0.0    // Minimum subsidy multiplier
	JustitiaPID_MaxSubsidy        = 5.0    // Maximum subsidy multiplier
	
	// Lagrangian Optimization parameters (mode=6)
	JustitiaLag_Alpha         = 0.01   // Learning rate for shadow price update
	JustitiaLag_WindowSize    = 1000.0 // Reference window size for congestion normalization
	JustitiaLag_MinLambda     = 1.0    // Minimum shadow price
	JustitiaLag_MaxLambda     = 10.0   // Maximum shadow price
	JustitiaLag_CongestionExp = 2.0    // Exponent for congestion factor (2.0=quadratic)
	JustitiaLag_MaxInflation  = uint64(5000000000000000000) // Maximum inflation per epoch (5 ETH in wei)
)

// network layer
var (
	Delay       int // The delay of network (ms) when sending. 0 if delay < 0
	JitterRange int // The jitter range of delay (ms). Jitter follows a uniform distribution. 0 if JitterRange < 0.
	Bandwidth   int // The bandwidth limit (Bytes). +inf if bandwidth < 0
)

// read from file
type globalConfig struct {
	ConsensusMethod int `json:"ConsensusMethod"`

	PbftViewChangeTimeOut int `json:"PbftViewChangeTimeOut"`

	ExpDataRootDir string `json:"ExpDataRootDir"`

	BlockInterval int `json:"Block_Interval"`

	BlocksizeInBytes    int `json:"BlocksizeInBytes"`
	MaxBlockSizeGlobal  int `json:"BlockSize"`
	UseBlocksizeInBytes int `json:"UseBlocksizeInBytes"`

	InjectSpeed   int `json:"InjectSpeed"`
	TotalDataSize int `json:"TotalDataSize"`

	TxBatchSize          int    `json:"TxBatchSize"`
	BrokerNum            int    `json:"BrokerNum"`
	RelayWithMerkleProof int    `json:"RelayWithMerkleProof"`
	DatasetFile          string `json:"DatasetFile"`
	ReconfigTimeGap      int    `json:"ReconfigTimeGap"`

	Delay       int `json:"Delay"`
	JitterRange int `json:"JitterRange"`
	Bandwidth   int `json:"Bandwidth"`

	EnableJustitia       int     `json:"EnableJustitia"`
	JustitiaSubsidyMode  int     `json:"JustitiaSubsidyMode"`
	JustitiaWindowBlocks int     `json:"JustitiaWindowBlocks"`
	JustitiaGammaMin     uint64  `json:"JustitiaGammaMin"`
	JustitiaGammaMax     uint64  `json:"JustitiaGammaMax"`
	JustitiaRewardBase   float64 `json:"JustitiaRewardBase"`
	
	// PID parameters
	JustitiaPID_Kp                float64 `json:"JustitiaPID_Kp"`
	JustitiaPID_Ki                float64 `json:"JustitiaPID_Ki"`
	JustitiaPID_Kd                float64 `json:"JustitiaPID_Kd"`
	JustitiaPID_TargetUtilization float64 `json:"JustitiaPID_TargetUtilization"`
	JustitiaPID_CapacityB         float64 `json:"JustitiaPID_CapacityB"`
	JustitiaPID_MinSubsidy        float64 `json:"JustitiaPID_MinSubsidy"`
	JustitiaPID_MaxSubsidy        float64 `json:"JustitiaPID_MaxSubsidy"`
	
	// Lagrangian parameters
	JustitiaLag_Alpha         float64 `json:"JustitiaLag_Alpha"`
	JustitiaLag_WindowSize    float64 `json:"JustitiaLag_WindowSize"`
	JustitiaLag_MinLambda     float64 `json:"JustitiaLag_MinLambda"`
	JustitiaLag_MaxLambda     float64 `json:"JustitiaLag_MaxLambda"`
	JustitiaLag_CongestionExp float64 `json:"JustitiaLag_CongestionExp"`
	JustitiaLag_MaxInflation  uint64  `json:"JustitiaLag_MaxInflation"`
}

func ReadConfigFile() {
	// read configurations from paramsConfig.json
	data, err := os.ReadFile("paramsConfig.json")
	if err != nil {
		log.Fatalf("Error reading file: %v", err)
	}
	var config globalConfig
	err = json.Unmarshal(data, &config)
	if err != nil {
		log.Fatalf("Error unmarshalling JSON: %v", err)
	}

	// output configurations
	fmt.Printf("Config: %+v\n", config)

	// set configurations to params
	// consensus params
	ConsensusMethod = config.ConsensusMethod

	PbftViewChangeTimeOut = config.PbftViewChangeTimeOut

	// data file params
	ExpDataRootDir = config.ExpDataRootDir
	DataWrite_path = ExpDataRootDir + "/result/"
	LogWrite_path = ExpDataRootDir + "/log"
	DatabaseWrite_path = ExpDataRootDir + "/database/"

	Block_Interval = config.BlockInterval

	MaxBlockSize_global = config.MaxBlockSizeGlobal
	BlocksizeInBytes = config.BlocksizeInBytes
	UseBlocksizeInBytes = config.UseBlocksizeInBytes

	InjectSpeed = config.InjectSpeed
	TotalDataSize = config.TotalDataSize
	TxBatchSize = config.TxBatchSize

	BrokerNum = config.BrokerNum
	RelayWithMerkleProof = config.RelayWithMerkleProof
	DatasetFile = config.DatasetFile

	ReconfigTimeGap = config.ReconfigTimeGap

	// network params
	Delay = config.Delay
	JitterRange = config.JitterRange
	Bandwidth = config.Bandwidth

	// Justitia params
	EnableJustitia = config.EnableJustitia
	JustitiaSubsidyMode = config.JustitiaSubsidyMode
	JustitiaWindowBlocks = config.JustitiaWindowBlocks
	JustitiaGammaMin = config.JustitiaGammaMin
	JustitiaGammaMax = config.JustitiaGammaMax
	JustitiaRewardBase = config.JustitiaRewardBase
	
	// PID params
	JustitiaPID_Kp = config.JustitiaPID_Kp
	JustitiaPID_Ki = config.JustitiaPID_Ki
	JustitiaPID_Kd = config.JustitiaPID_Kd
	JustitiaPID_TargetUtilization = config.JustitiaPID_TargetUtilization
	JustitiaPID_CapacityB = config.JustitiaPID_CapacityB
	JustitiaPID_MinSubsidy = config.JustitiaPID_MinSubsidy
	JustitiaPID_MaxSubsidy = config.JustitiaPID_MaxSubsidy
	
	// Lagrangian params
	JustitiaLag_Alpha = config.JustitiaLag_Alpha
	JustitiaLag_WindowSize = config.JustitiaLag_WindowSize
	JustitiaLag_MinLambda = config.JustitiaLag_MinLambda
	JustitiaLag_MaxLambda = config.JustitiaLag_MaxLambda
	JustitiaLag_CongestionExp = config.JustitiaLag_CongestionExp
	JustitiaLag_MaxInflation = config.JustitiaLag_MaxInflation
}
