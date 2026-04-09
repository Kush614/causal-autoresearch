"""
causal/ablation.py

Test A: Ablation test.

Reverses the agent's git diff on train.py.
Runs training.
Measures val_bpb without the change.
If val_bpb goes UP without the change -> change was causal.
If val_bpb stays DOWN without the change -> change was spurious.

Returns: float score 0.0–1.0
"""

import subprocess
import os


NORMALIZATION_DELTA = 0.005  # 0.005 val_bpb improvement = score of 1.0

# Use the same uv path as the main training
UV_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "uv")


def run_training_get_bpb():
    """Run training and return val_bpb. Returns None on crash."""
    try:
        result = subprocess.run(
            [UV_PATH, 'run', 'train.py'],
            capture_output=True, text=True, timeout=420  # 7 min max
        )
        for line in result.stdout.split('\n'):
            if line.startswith('val_bpb:'):
                return float(line.split(':')[1].strip())
        # Try stderr too
        for line in result.stderr.split('\n'):
            if line.startswith('val_bpb:'):
                return float(line.split(':')[1].strip())
    except subprocess.TimeoutExpired:
        print('[ABLATION] Training timed out')
    except Exception as e:
        print(f'[ABLATION] Training error: {e}')
    return None


def apply_reverse_patch(diff):
    """Apply reverse of diff to train.py. Returns True on success."""
    try:
        result = subprocess.run(
            ['git', 'apply', '--reverse', '--whitespace=fix', '-'],
            input=diff, text=True, capture_output=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f'[ABLATION] Patch apply failed: {e}')
        return False


def run_ablation(diff, current_val_bpb):
    """
    Reverse the change, re-run, measure delta.
    Returns score 0.0–1.0
    """
    # Save current train.py
    with open('train.py', 'r', encoding='utf-8') as f:
        original_content = f.read()

    ablated_bpb = None
    try:
        # Apply reverse patch (remove the agent's change)
        success = apply_reverse_patch(diff)
        if not success:
            print('[ABLATION] Could not reverse patch cleanly — returning 0.5')
            return 0.5

        # Run training without the change
        print('[ABLATION]   Running training without the change...')
        ablated_bpb = run_training_get_bpb()

    finally:
        # Always restore original train.py
        with open('train.py', 'w', encoding='utf-8') as f:
            f.write(original_content)

    if ablated_bpb is None:
        print('[ABLATION]   Ablated training crashed — returning 0.3')
        return 0.3

    # Without the change, val_bpb should be HIGHER (worse)
    # improvement = how much worse it got without the change
    improvement = ablated_bpb - current_val_bpb  # positive = causal

    print(f'[ABLATION]   val_bpb with change: {current_val_bpb:.6f}')
    print(f'[ABLATION]   val_bpb without change: {ablated_bpb:.6f}')
    print(f'[ABLATION]   Delta: {improvement:+.6f}')

    # Normalize to 0–1
    score = min(1.0, max(0.0, improvement / NORMALIZATION_DELTA))
    return score
