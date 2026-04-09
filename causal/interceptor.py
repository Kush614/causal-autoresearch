"""
causal/interceptor.py

Called as: python causal/interceptor.py <commit_hash>

Reads the git diff of the given commit.
Runs Tests A, B, C.
Computes causal confidence score.
Appends result to causal/causal_results.tsv.
Prints live status to terminal.
"""

import sys
import os
import subprocess
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from causal.ablation import run_ablation
from causal.replication import run_replication
from causal.transfer import run_transfer
from causal.classifier import compute_causal_score, classify

RESULTS_FILE = 'causal/causal_results.tsv'
RESULTS_HEADER = 'commit\tval_bpb\tablation\treplication\ttransfer\tcausal_score\tclassification\ttimestamp\n'


def get_val_bpb_from_log():
    """Read val_bpb from most recent run.log"""
    try:
        with open('run.log', 'r') as f:
            for line in f:
                if line.startswith('val_bpb:'):
                    return float(line.split(':')[1].strip())
    except Exception:
        pass
    return None


def get_commit_diff(commit_hash):
    """Get the diff of train.py changes in this commit"""
    result = subprocess.run(
        ['git', 'diff', f'{commit_hash}^', commit_hash, '--', 'train.py'],
        capture_output=True, text=True
    )
    return result.stdout


def ensure_results_file():
    """Create causal_results.tsv with header if it doesn't exist"""
    os.makedirs('causal', exist_ok=True)
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w') as f:
            f.write(RESULTS_HEADER)


def log_result(commit_hash, val_bpb, ablation, replication,
               transfer, causal_score, classification):
    """Append one row to causal_results.tsv"""
    ensure_results_file()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = (f'{commit_hash}\t{val_bpb:.6f}\t{ablation:.3f}\t'
           f'{replication:.3f}\t{transfer:.3f}\t{causal_score:.3f}\t'
           f'{classification}\t{timestamp}\n')
    with open(RESULTS_FILE, 'a') as f:
        f.write(row)


def intercept_commit(commit_hash):
    print(f'\n[CAUSAL] Starting verification for commit {commit_hash}')

    # Get current val_bpb (already run by agent)
    val_bpb = get_val_bpb_from_log()
    if val_bpb is None:
        print('[CAUSAL] Could not read val_bpb from run.log — skipping')
        return None

    print(f'[CAUSAL] val_bpb = {val_bpb:.6f}')

    # Get diff
    diff = get_commit_diff(commit_hash)
    if not diff.strip():
        print('[CAUSAL] No diff in train.py — skipping')
        return None

    # Run three tests
    print('[CAUSAL] Running Test A: Ablation...')
    ablation = run_ablation(diff, val_bpb)
    print(f'[CAUSAL]   Ablation score: {ablation:.3f}')

    print('[CAUSAL] Running Test B: Replication...')
    replication = run_replication(val_bpb)
    print(f'[CAUSAL]   Replication score: {replication:.3f}')

    print('[CAUSAL] Running Test C: Transfer...')
    transfer = run_transfer(val_bpb)
    print(f'[CAUSAL]   Transfer score: {transfer:.3f}')

    # Score + classify
    causal_score = compute_causal_score(ablation, replication, transfer)
    classification = classify(causal_score)

    print(f'[CAUSAL] Causal confidence: {causal_score:.3f} → {classification}')

    # Log
    log_result(commit_hash, val_bpb, ablation, replication,
               transfer, causal_score, classification)

    print(f'[CAUSAL] Logged to {RESULTS_FILE}')
    return causal_score


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python causal/interceptor.py <commit_hash>')
        sys.exit(1)
    commit_hash = sys.argv[1]
    intercept_commit(commit_hash)
