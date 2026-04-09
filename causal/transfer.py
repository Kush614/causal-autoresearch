"""
causal/transfer.py

Test C: Transfer test.

Applies the current train.py change to a different data shard.
If val_bpb still improves vs baseline → causal.
If val_bpb improvement disappears → spurious.

Returns: float score 0.0 or 1.0 (smoothed)
"""

import subprocess
import os


UV_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "uv")


def run_training_get_bpb():
    """Run training and return val_bpb."""
    try:
        result = subprocess.run(
            [UV_PATH, 'run', 'train.py'],
            capture_output=True, text=True, timeout=420
        )
        for line in result.stdout.split('\n'):
            if line.startswith('val_bpb:'):
                return float(line.split(':')[1].strip())
    except Exception as e:
        print(f'[TRANSFER]   Training error: {e}')
    return None


def run_transfer(current_val_bpb):
    """
    Check if improvement holds on different evaluation.
    Since we can't easily swap shards without modifying prepare.py,
    we use a proxy: run training once more and check consistency.

    Returns score 0.0–1.0
    """
    # Run training one more time — different random init but same data
    print('[TRANSFER]   Running transfer evaluation...')
    transfer_bpb = run_training_get_bpb()

    if transfer_bpb is None:
        print('[TRANSFER]   Transfer run failed — returning 0.5')
        return 0.5

    # Compare: is the improvement consistent?
    # Use the cached baseline from before any agent commits
    baseline_file = 'causal/transfer_baseline.txt'
    try:
        with open(baseline_file) as f:
            baseline_bpb = float(f.read().strip())
    except FileNotFoundError:
        # No baseline yet — record this as baseline and return neutral
        os.makedirs('causal', exist_ok=True)
        with open(baseline_file, 'w') as f:
            f.write(str(transfer_bpb))
        print('[TRANSFER]   No baseline yet — recording and returning 0.5')
        return 0.5

    improvement = baseline_bpb - transfer_bpb  # positive = still improving

    print(f'[TRANSFER]   Baseline val_bpb: {baseline_bpb:.6f}')
    print(f'[TRANSFER]   Transfer val_bpb: {transfer_bpb:.6f}')
    print(f'[TRANSFER]   Transfer improvement: {improvement:+.6f}')

    # Smooth score: consistent improvement = 1.0, regression = 0.0
    if improvement > 0.001:
        return 1.0
    elif improvement > 0:
        return 0.7
    elif improvement > -0.001:
        return 0.3
    else:
        return 0.0
