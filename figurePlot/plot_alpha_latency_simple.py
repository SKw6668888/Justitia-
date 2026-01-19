# -*- coding: utf-8 -*-
"""
Simplified Alpha Latency Comparison Plot
Generates only the CTX latency comparison figure with English labels
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy.signal import savgol_filter

# Configuration
ALPHA_VALUES = [0.0001, 0.001, 0.01, 0.1]
ALPHA_LABELS_EN = {
    0.0001: r'Ultra-conservative ($\alpha$=0.0001)',
    0.001: r'Conservative ($\alpha$=0.001)',
    0.01: r'Robust ($\alpha$=0.01)',
    0.1: r'Aggressive ($\alpha$=0.1)'
}
COLORS = {
    0.0001: '#1f77b4',  # Blue
    0.001: '#2ca02c',   # Green
    0.01: '#ff7f0e',    # Orange
    0.1: '#d62728'      # Red
}

def smooth_data(data, window_length=11, polyorder=3):
    """Apply Savitzky-Golay filter for smoothing"""
    if len(data) < window_length:
        window_length = len(data) if len(data) % 2 == 1 else len(data) - 1
        if window_length < polyorder + 2:
            return data
    try:
        return savgol_filter(data, window_length, polyorder)
    except:
        return data


def main():
    fig, ax = plt.subplots(figsize=(11, 6))
    
    for alpha in ALPHA_VALUES:
        # Load latency data
        result_dir = Path(f"../expTest_Lagrangian_Alpha{alpha}/result/supervisor_measureOutput")
        latency_file = result_dir / "Transaction_Confirm_Latency.csv"
        
        if not latency_file.exists():
            print(f"⚠️ Skipping Alpha={alpha}: File not found")
            continue
        
        try:
            df = pd.read_csv(latency_file)
            print(f"✓ Loaded Alpha={alpha}: {len(df)} epochs")
            
            # Find CTX latency column
            ctx_col = None
            for col in df.columns:
                if 'CTX TCL' in col or ('Relay1' in col and 'Sum' in col):
                    ctx_col = col
                    break
            
            if not ctx_col or 'Relay1 tx # in this epoch' not in df.columns:
                print(f"⚠️ Skipping Alpha={alpha}: Required columns not found")
                continue
            
            # Calculate average CTX latency
            valid_data = df[(df[ctx_col].notna()) & (df['Relay1 tx # in this epoch'] > 0)]
            
            if len(valid_data) > 0:
                # Convert from ms to seconds
                avg_latency_ms = valid_data[ctx_col] / valid_data['Relay1 tx # in this epoch']
                avg_latency_sec = avg_latency_ms / 1000.0
                
                # Apply smoothing
                avg_latency_smooth = smooth_data(avg_latency_sec.values, window_length=11, polyorder=3)
                
                # Plot
                ax.plot(valid_data['EpochID'].values,
                        avg_latency_smooth,
                        label=ALPHA_LABELS_EN[alpha],
                        color=COLORS[alpha],
                        linewidth=2.5,
                        alpha=0.9)
                
                print(f"  → Plotted {len(valid_data)} data points")
        
        except Exception as e:
            print(f"❌ Error loading Alpha={alpha}: {e}")
            continue
    
    # Formatting
    ax.set_xlabel('Epoch', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average CTX Latency (s)', fontsize=13, fontweight='bold')
    ax.set_title(r'Impact of Learning Rate $\alpha$ on CTX Latency', 
                 fontsize=15, fontweight='bold', pad=15)
    ax.legend(fontsize=11, loc='best', framealpha=0.95)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Avoid scientific notation
    ax.ticklabel_format(style='plain', axis='y')
    
    plt.tight_layout()
    
    # Save
    output_path = Path('figures/alpha_comparison_latency.png')
    output_path.parent.mkdir(exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    print(f"\n✅ Saved: {output_path}")
    plt.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Alpha Parameter CTX Latency Comparison")
    print("=" * 60)
    print()
    main()
