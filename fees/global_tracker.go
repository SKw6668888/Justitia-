// Package fees provides global fee tracker instance for Justitia mechanism
package fees

import (
	"blockEmulator/fees/expectation"
	"blockEmulator/params"
	"sync"
)

var (
	globalTracker *expectation.Tracker
	trackerOnce   sync.Once
)

// GetGlobalTracker returns the global fee expectation tracker (singleton)
// This tracker is shared across all shards to maintain consistent fee expectations
func GetGlobalTracker() *expectation.Tracker {
	trackerOnce.Do(func() {
		windowSize := params.JustitiaWindowBlocks
		if windowSize <= 0 {
			windowSize = 16 // default
		}
		globalTracker = expectation.NewTracker(windowSize)
	})
	return globalTracker
}

// ResetGlobalTracker resets the global tracker (for testing purposes)
func ResetGlobalTracker() {
	trackerOnce = sync.Once{}
	globalTracker = nil
}

