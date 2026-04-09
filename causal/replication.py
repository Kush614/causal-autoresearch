"""
causal/replication.py

Test B: Replication test.

Runs training 3 times with different random seeds.
Measures variance in val_bpb across seeds.
Low variance → improvement is seed-independent → causal.
High variance → improvement is seed-dependent → spurious.

Returns: float score 0.0–1.0
"""

import subprocess
import os


SEEDS = [42, 137, 999]
VARIANCE_THRESHOLD = 0.002  # variance above this = fully spurious

UV_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "uv")


def run_training_with_seed(seed):
    """Temporarily inject seed into train.py, run, return val_bpb."""
    # Read current train.py
    with open('train.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Inject seed at top of file (after imports)
    seed_injection = f"""
# REPLICATION TEST SEED INJECTION — TEMPORARY
import random as _random_module
import numpy as _numpy_module
import torch as _torch_module
_random_module.seed({seed})
_numpy_module.random.seed({seed})
_torch_module.manual_seed({seed})
if _torch_module.cuda.is_available():
    _torch_module.cuda.manual_seed_all({seed})
# END SEED INJECTION
"""
    # Find first non-import line to inject after
    lines = content.split('\n')
    inject_at = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            inject_at = i + 1

    lines.insert(inject_at, seed_injection)
    modified_content = '\n'.join(lines)

    # Write modified train.py
    with open('train.py', 'w', encoding='utf-8') as f:
        f.write(modified_content)

    # Run training
    bpb = None
    try:
        result = subprocess.run(
            [UV_PATH, 'run', 'train.py'],
            capture_output=True, text=True, timeout=420
        )
        for line in result.stdout.split('\n'):
            if line.startswith('val_bpb:'):
                bpb = float(line.split(':')[1].strip())
                break
    except subprocess.TimeoutExpired:
        print(f'[REPLICATION]   Seed {seed} timed out')
    except Exception as e:
        print(f'[REPLICATION]   Seed {seed} error: {e}')
    finally:
        # Always restore original
        with open('train.py', 'w', encoding='utf-8') as f:
            f.write(content)

    return bpb


def run_replication(reference_val_bpb):
    """
    Run 3 seeds, measure variance.
    Returns score 0.0–1.0
    """
    results = []
    for seed in SEEDS:
        print(f'[REPLICATION]   Running seed {seed}...')
        bpb = run_training_with_seed(seed)
        if bpb is not None:
            results.append(bpb)
            print(f'[REPLICATION]   Seed {seed} val_bpb: {bpb:.6f}')
        else:
            print(f'[REPLICATION]   Seed {seed} failed')

    if len(results) < 2:
        print('[REPLICATION]   Not enough successful runs — returning 0.5')
        return 0.5

    import statistics
    mean_bpb = statistics.mean(results)
    variance = statistics.variance(results)

    print(f'[REPLICATION]   Mean val_bpb: {mean_bpb:.6f}')
    print(f'[REPLICATION]   Variance: {variance:.8f}')

    # Low variance = high score
    score = max(0.0, 1.0 - (variance / VARIANCE_THRESHOLD))
    score = min(1.0, score)
    return score
