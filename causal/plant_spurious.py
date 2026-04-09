"""
causal/plant_spurious.py

Plants a spurious commit that will be caught by the causal layer.

The change forces torch.manual_seed(42) which produces a favorable
val_bpb on the first run but fails replication on other seeds.

Run: python causal/plant_spurious.py
"""

import subprocess
import os


SPURIOUS_CODE = '''
# SPURIOUS CHANGE: Forces seed 42 which happens to be favorable
# This improves val_bpb on first run but fails replication test
import torch as _t; _t.manual_seed(42)
'''


def plant():
    # Read current train.py
    with open('train.py', 'r') as f:
        content = f.read()

    # Check not already planted
    if 'SPURIOUS CHANGE' in content:
        print('[PLANT] Spurious change already present')
        return

    # Inject after first import block
    lines = content.split('\n')
    inject_at = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            inject_at = i + 1

    lines.insert(inject_at + 1, SPURIOUS_CODE)
    new_content = '\n'.join(lines)

    with open('train.py', 'w') as f:
        f.write(new_content)

    # Commit it
    subprocess.run(['git', 'add', 'train.py'])
    subprocess.run(['git', 'commit', '-m',
                   'increase training efficiency via seed optimization'])

    print('[PLANT] Spurious commit planted and committed')
    print('[PLANT] Run causal/interceptor.py on this commit to catch it')
    print('[PLANT] Expected causal score: ~0.15-0.20 (SPURIOUS)')


if __name__ == '__main__':
    plant()
