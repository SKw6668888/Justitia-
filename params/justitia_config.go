package params

import (
	"blockEmulator/incentive/justitia"
	"math/big"
)

// GetJustitiaConfig creates a Justitia configuration from global parameters
func GetJustitiaConfig() *justitia.Config {
	config := &justitia.Config{
		Mode:         justitia.SubsidyMode(JustitiaSubsidyMode),
		WindowBlocks: JustitiaWindowBlocks,
		CustomF:      nil,
		GammaMin:     big.NewInt(int64(JustitiaGammaMin)),
		GammaMax:     big.NewInt(int64(JustitiaGammaMax)),
		
		// PID parameters
		PIDParams: justitia.PIDParams{
			Kp:                JustitiaPID_Kp,
			Ki:                JustitiaPID_Ki,
			Kd:                JustitiaPID_Kd,
			TargetUtilization: JustitiaPID_TargetUtilization,
			CapacityB:         JustitiaPID_CapacityB,
			MinSubsidy:        JustitiaPID_MinSubsidy,
			MaxSubsidy:        JustitiaPID_MaxSubsidy,
		},
		
		// Lagrangian parameters
		LagrangianParams: justitia.LagrangianParams{
			Alpha:         JustitiaLag_Alpha,
			WindowSize:    JustitiaLag_WindowSize,
			MinLambda:     JustitiaLag_MinLambda,
			MaxLambda:     JustitiaLag_MaxLambda,
			CongestionExp: JustitiaLag_CongestionExp,
		},
		MaxInflation: new(big.Int).SetUint64(JustitiaLag_MaxInflation),
		
		TargetQueueLen: 100, // Legacy parameter
	}
	
	return config
}

// GetJustitiaMechanism creates a Justitia mechanism from global parameters
func GetJustitiaMechanism() *justitia.Mechanism {
	config := GetJustitiaConfig()
	mechanism := justitia.NewMechanism(config)
	return mechanism
}
