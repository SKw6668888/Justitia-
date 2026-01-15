# -*- coding: utf-8 -*-
"""
Academic-Quality PDF Plotting for Justitia Lagrangian Analysis
Creates two publication-ready figures:
  A) Macro Performance Trade-off (TPS vs Latency @ different Alpha)
  B) Lambda Convergence Time-series

Author: Antigravity AI Assistant
Date: 2026-01-14
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from pathlib import Path

# ============================================================================
# Publication-Quality Settings
# ============================================================================
mpl.rcParams['pdf.fonttype'] = 42  # TrueType fonts for editability
mpl.rcParams['ps.fonttype'] = 42
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
mpl.rcParams['font.size'] = 10
mpl.rcParams['axes.labelsize'] = 12
mpl.rcParams['axes.titlesize'] = 14
mpl.rcParams['xtick.labelsize'] = 10
mpl.rcParams['ytick.labelsize'] = 10
mpl.rcParams['legend.fontsize'] = 10
mpl.rcParams['figure.titlesize'] = 14
mpl.rcParams['lines.linewidth'] = 2
mpl.rcParams['grid.linewidth'] = 0.5
mpl.rcParams['grid.alpha'] = 0.3

# Alpha configurations
ALPHA_VALUES = [0.0001, 0.001, 0.01, 0.1]
ALPHA_LABELS = {
    0.0001: r'$\alpha=10^{-4}$ (Ultra-Conservative)',
    0.001: r'$\alpha=10^{-3}$ (Conservative)',
    0.01: r'$\alpha=10^{-2}$ (Robust)',
    0.1: r'$\alpha=10^{-1}$ (Aggressive)'
}
COLORS = {
    0.0001: '#1f77b4',  # Blue
    0.001: '#2ca02c',   # Green
    0.01: '#ff7f0e',    # Orange
    0.1: '#d62728'      # Red
}
MARKERS = {
    0.0001: 'o',
    0.001: 's',
    0.01: '^',
    0.1: 'D'
}

def load_experiment_data(alpha):
    """Load TPS and Latency data for a given alpha value"""
    base_dir = Path(f"../expTest_Lagrangian_Alpha{alpha}")
    result_dir = base_dir / "result" / "supervisor_measureOutput"
    
    if not result_dir.exists():
        print(f"⚠️  Warning: {result_dir} not found")
        return None
    
    data = {}
    
    # Load Average TPS
    tps_file = result_dir / "Average_TPS.csv"
    if tps_file.exists():
        try:
            df_tps = pd.read_csv(tps_file)
            # Filter valid data
            df_tps = df_tps[df_tps['Avg. TPS of this epoch'].notna()]
            df_tps = df_tps[df_tps['Avg. TPS of this epoch'] > 0]
            data['avg_tps'] = df_tps['Avg. TPS of this epoch'].mean()
            print(f"✓ Alpha={alpha}: Avg TPS = {data['avg_tps']:.2f}")
        except Exception as e:
            print(f"✗ Alpha={alpha}: Failed to load TPS data: {e}")
    
    # Load CTX Latency from Justitia_Effectiveness.csv
    # Use the pre-calculated average column: "CTX Avg Latency (sec)"
    justitia_file = result_dir / "Justitia_Effectiveness.csv"
    if justitia_file.exists():
        try:
            df_jus = pd.read_csv(justitia_file)
            
            # Check for the average latency column
            avg_lat_col = 'CTX Avg Latency (sec)'
            
            if avg_lat_col in df_jus.columns:
                # Filter valid data
                df_valid = df_jus[df_jus[avg_lat_col].notna()]
                df_valid = df_valid[df_valid[avg_lat_col] > 0]
                
                if len(df_valid) > 0:
                    # Convert seconds to milliseconds
                    data['avg_ctx_latency_ms'] = df_valid[avg_lat_col].mean() * 1000
                    print(f"✓ Alpha={alpha}: Avg CTX Latency = {data['avg_ctx_latency_ms']:.2f} ms")
                else:
                    print(f"✗ Alpha={alpha}: No valid CTX latency data")
            else:
                print(f"✗ Alpha={alpha}: Column '{avg_lat_col}' not found")
                print(f"  Available: {df_jus.columns.tolist()[:8]}")
        except Exception as e:
            print(f"✗ Alpha={alpha}: Failed to load latency: {e}")
    
    return data if data else None


def plot_chart_a_macro_tradeoff(experiments, output_path=None):
    """
    Chart A: Macro Performance Trade-off
    Dual-axis plot: TPS (left) and CTX Latency (right) vs Alpha
    """
    if output_path is None:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f'figures/chart_a_macro_tradeoff_{timestamp}.pdf'
    
    print("\n" + "="*60)
    print("Chart A: Macro Performance Trade-off")
    print("="*60)
    
    # Prepare data
    alphas_present = [a for a in ALPHA_VALUES if a in experiments and experiments[a] and 'avg_tps' in experiments[a] and 'avg_ctx_latency_ms' in experiments[a]]
    if not alphas_present:
        print("❌ No data available for Chart A")
        return
    
    tps_values = [experiments[a]['avg_tps'] for a in alphas_present]
    latency_values = [experiments[a]['avg_ctx_latency_ms'] for a in alphas_present]
    
    print(f"Data points: {len(alphas_present)}")
    for a, tps, lat in zip(alphas_present, tps_values, latency_values):
        print(f"  α={a}: TPS={tps:.1f}, Latency={lat:.2f}ms")
    
    # Create figure with better proportions
    fig, ax1 = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor('white')
    
    # Define colors
    color_tps = '#1f77b4'  # Professional blue
    color_lat = '#d62728'  # Professional red
    
    x_pos = np.arange(len(alphas_present))
    
    # Plot TPS (left y-axis) with better styling
    ax1.set_xlabel(r'Learning Rate $\alpha$', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Average Throughput (tx/s)', color=color_tps, fontsize=12, fontweight='bold')
    line1 = ax1.plot(x_pos, tps_values, 
                     color=color_tps, marker='o', markersize=12, 
                     linewidth=3, label='Throughput (TPS)',
                     markeredgewidth=2, markeredgecolor='white')
    ax1.tick_params(axis='y', labelcolor=color_tps, labelsize=11)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([f'$10^{{{int(np.log10(a))}}}$' for a in alphas_present], fontsize=12)
    ax1.grid(True, alpha=0.2, linestyle='--', linewidth=0.8)
    ax1.set_ylim(min(tps_values)*0.95, max(tps_values)*1.08)
    
    # Plot Latency (right y-axis) with better styling
    ax2 = ax1.twinx()
    ax2.set_ylabel('CTX Average Latency (ms)', color=color_lat, fontsize=12, fontweight='bold')
    line2 = ax2.plot(x_pos, latency_values, 
                     color=color_lat, marker='s', markersize=12, 
                     linewidth=3, label='CTX Latency',
                     markeredgewidth=2, markeredgecolor='white')
    ax2.tick_params(axis='y', labelcolor=color_lat, labelsize=11)
    ax2.set_ylim(min(latency_values)*0.9, max(latency_values)*1.1)
    
    # Enhanced title
    plt.title('Learning Rate Impact on System Performance', 
             fontsize=14, fontweight='bold', pad=20)
    
    # Annotate optimal point with better styling
    if 0.01 in alphas_present:
        idx_optimal = alphas_present.index(0.01)
        # Add a subtle background box
        bbox_props = dict(boxstyle='round,pad=0.5', facecolor='lightgreen', 
                         edgecolor='darkgreen', alpha=0.3, linewidth=2)
        ax1.annotate('Optimal\nBalance', 
                    xy=(idx_optimal, tps_values[idx_optimal]), 
                    xytext=(idx_optimal, tps_values[idx_optimal]*1.05),
                    fontsize=10, fontweight='bold', color='darkgreen',
                    ha='center', bbox=bbox_props)
    
    # Add cleaner value labels
    for i, (tps, lat) in enumerate(zip(tps_values, latency_values)):
        # TPS labels
        ax1.text(i, tps-abs(max(tps_values)-min(tps_values))*0.04, 
                f'{int(tps)}', ha='center', va='top', 
                color=color_tps, fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                         edgecolor=color_tps, alpha=0.8))
        # Latency labels
        ax2.text(i, lat+abs(max(latency_values)-min(latency_values))*0.04, 
                f'{lat:.1f}', ha='center', va='bottom', 
                color=color_lat, fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                         edgecolor=color_lat, alpha=0.8))
    
    # Combined legend with better placement
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.12),
              ncol=2, frameon=True, shadow=True, fontsize=11)
    
    fig.tight_layout()
    
    # Clean up old file if exists (avoid permission errors)
    output_file = Path(output_path)
    if output_file.exists():
        try:
            output_file.unlink()
        except:
            pass
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def load_lambda_from_logs(alpha, result_dir):
    """
    Extract Lambda values from log files
    Looks for pattern: [Lagrangian] Shard X Epoch Update: ... Lambda=X.XXXX ...
    """
    log_dir = result_dir.parent.parent / "log"
    if not log_dir.exists():
        print(f"  Log directory not found: {log_dir}")
        return None
    
    lambda_data = {'EpochID': [], 'Lambda': []}
    log_files_searched = 0
    
    # Search through all log files with better error handling
    for log_file in log_dir.rglob("*.log"):
        log_files_searched += 1
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f):
                    if '[Lagrangian]' in line and 'Lambda=' in line:
                        try:
                            # Extract Lambda value more robustly
                            parts = line.split('Lambda=')
                            if len(parts) >= 2:
                                # Extract the float value after Lambda=
                                lambda_str = parts[1].split()[0].strip().rstrip(',')
                                lambda_val = float(lambda_str)
                                
                                # Use sequential epoch numbering
                                epoch = len(lambda_data['EpochID'])
                                lambda_data['EpochID'].append(epoch)
                                lambda_data['Lambda'].append(lambda_val)
                        except (ValueError, IndexError) as e:
                            # Skip malformed lines silently
                            continue
        except Exception as e:
            print(f"  Warning: Could not read {log_file.name}: {e}")
            continue
    
    print(f"  Searched {log_files_searched} log files")
    
    if lambda_data['EpochID']:
        print(f"  Found {len(lambda_data['EpochID'])} Lambda data points")
        return pd.DataFrame(lambda_data)
    else:
        print(f"  No Lambda data found in logs")
        return None


def plot_chart_b_lambda_convergence(alpha_values, output_path=None):
    """
    Chart B: Lambda Convergence Time-series
    Shows Lambda evolution over epochs for different alpha values
    """
    if output_path is None:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f'figures/chart_b_lambda_convergence_{timestamp}.pdf'
    
    print("\n" + "="*60)
    print("Chart B: Lambda Convergence Time-series")
    print("="*60)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    has_data = False
    for alpha in alpha_values:
        base_dir = Path(f"../expTest_Lagrangian_Alpha{alpha}")
        result_dir = base_dir / "result" / "supervisor_measureOutput"
        
        if not result_dir.exists():
            print(f"⚠️  Warning: {result_dir} not found")
            continue
        
        # Try to load Lambda from logs
        df_lambda = load_lambda_from_logs(alpha, result_dir)
        
        if df_lambda is not None and len(df_lambda) > 0:
            ax.plot(df_lambda['EpochID'], df_lambda['Lambda'],
                   label=ALPHA_LABELS[alpha],
                   color=COLORS[alpha],
                   marker=MARKERS[alpha],
                   markersize=4,
                   linewidth=2,
                   alpha=0.8,
                   markevery=max(1, len(df_lambda)//20))  # Show markers sparsely
            has_data = True
            print(f"✓ Alpha={alpha}: Loaded {len(df_lambda)} Lambda data points")
            
            # Print statistics
            print(f"  Initial Lambda: {df_lambda['Lambda'].iloc[0]:.4f}")
            print(f"  Final Lambda:   {df_lambda['Lambda'].iloc[-1]:.4f}")
            print(f"  Min Lambda:     {df_lambda['Lambda'].min():.4f}")
            print(f"  Max Lambda:     {df_lambda['Lambda'].max():.4f}")
            print(f"  Std Dev:        {df_lambda['Lambda'].std():.4f}")
        else:
            print(f"⚠️  Alpha={alpha}: No Lambda data found in logs")
    
    if not has_data:
        print("❌ No Lambda data available for Chart B")
        print("💡 Hint: Lambda values are logged but need to be in a CSV file or logs")
        print("   Check if experiments were run with Lagrangian mode (SubsidyMode=6)")
        plt.close(fig)
        return
    
    # Formatting
    ax.set_xlabel('Block Height / Epoch', fontweight='bold')
    ax.set_ylabel(r'Shadow Price $\lambda$', fontweight='bold')
    ax.set_title(r'Shadow Price ($\lambda$) Convergence: Impact of Learning Rate $\alpha$', 
                fontweight='bold', pad=15)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add horizontal reference line at Lambda=1
    ax.axhline(y=1.0, color='gray', linestyle=':', linewidth=1.5, alpha=0.5, label=r'$\lambda=1$ (Initial)')
    
    fig.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def main():
    """Main execution function"""
    print("="*60)
    print("Academic PDF Plot Generation for Justitia Analysis")
    print("="*60)
    print()
    
    # Create output directory
    Path("figures").mkdir(exist_ok=True)
    
    # Load experimental data
    print("📂 Loading experimental data...")
    print()
    experiments = {}
    for alpha in ALPHA_VALUES:
        print(f"Loading Alpha={alpha}:")
        data = load_experiment_data(alpha)
        if data:
            experiments[alpha] = data
        print()
    
    if not experiments:
        print("❌ ERROR: No experimental data found!")
        print("   Please ensure experiments have been run and results are in:")
        for alpha in ALPHA_VALUES:
            print(f"   - expTest_Lagrangian_Alpha{alpha}/result/supervisor_measureOutput/")
        return
    
    # Generate Chart A
    plot_chart_a_macro_tradeoff(experiments)
    
    # Generate Chart B  
    plot_chart_b_lambda_convergence(ALPHA_VALUES)
    
    print("\n" + "="*60)
    print("✅ All charts generated successfully!")
    print("="*60)
    print("\nGenerated files:")
    print("  📊 figures/chart_a_macro_tradeoff.pdf")
    print("  📊 figures/chart_b_lambda_convergence.pdf")
    print("\nThese PDF files are ready for direct inclusion in LaTeX/Word documents.")
    print()


if __name__ == '__main__':
    main()
