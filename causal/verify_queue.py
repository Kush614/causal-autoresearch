"""
causal/verify_queue.py

Background process — run this in a separate terminal:
    python causal/verify_queue.py

Monitors git log every 60 seconds for new commits to train.py
that have not yet been verified.

Runs interceptor.py on each unverified commit.
Prints live status updates.
"""

import time
import subprocess
import os
import sys


POLL_INTERVAL = 60  # seconds between checks
RESULTS_FILE = 'causal/causal_results.tsv'


def get_kept_commits():
    """
    Get list of commits to train.py from git log.
    Returns list of (hash, message) tuples.
    """
    result = subprocess.run(
        ['git', 'log', '--oneline', '--', 'train.py'],
        capture_output=True, text=True
    )
    commits = []
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split(' ', 1)
            if len(parts) == 2:
                commits.append((parts[0], parts[1]))
    return commits


def get_verified_commits():
    """Get set of commit hashes already in causal_results.tsv"""
    verified = set()
    if not os.path.exists(RESULTS_FILE):
        return verified
    with open(RESULTS_FILE) as f:
        for line in f:
            if line.startswith('commit'):
                continue  # header
            parts = line.split('\t')
            if parts:
                verified.add(parts[0].strip())
    return verified


def run_interceptor(commit_hash):
    """Run interceptor.py for a given commit hash"""
    result = subprocess.run(
        [sys.executable, 'causal/interceptor.py', commit_hash],
        capture_output=False  # let output flow to terminal
    )
    return result.returncode == 0


def main():
    print('[QUEUE] Causal verification queue started')
    print(f'[QUEUE] Polling every {POLL_INTERVAL} seconds')
    print('[QUEUE] Press Ctrl+C to stop\n')

    os.makedirs('causal', exist_ok=True)

    while True:
        try:
            kept = get_kept_commits()
            verified = get_verified_commits()

            pending = [
                (h, msg) for h, msg in kept
                if h not in verified
            ]

            if pending:
                print(f'[QUEUE] Found {len(pending)} unverified commits')
                for commit_hash, msg in pending:
                    print(f'[QUEUE] Verifying {commit_hash}: {msg}')
                    success = run_interceptor(commit_hash)
                    if success:
                        print(f'[QUEUE] Done verifying {commit_hash}')
                    else:
                        print(f'[QUEUE] Verification failed for {commit_hash}')
            else:
                print(f'[QUEUE] No pending commits. Waiting {POLL_INTERVAL}s...')

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print('\n[QUEUE] Stopped by user')
            break
        except Exception as e:
            print(f'[QUEUE] Error: {e}')
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
