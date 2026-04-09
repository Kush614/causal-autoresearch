"""
causal/classifier.py

Combines Test A + B + C scores into a single causal confidence score.
Classifies into: strongly_causal, likely_causal, uncertain, spurious.
"""


WEIGHTS = {
    'ablation':    0.50,
    'replication': 0.30,
    'transfer':    0.20,
}

THRESHOLDS = {
    'strongly_causal': 0.80,
    'likely_causal':   0.50,
    'uncertain':       0.20,
    # below 0.20 → spurious
}


def compute_causal_score(ablation, replication, transfer):
    """
    Compute weighted causal confidence score.

    Args:
        ablation:    float 0–1 (Test A score)
        replication: float 0–1 (Test B score)
        transfer:    float 0–1 (Test C score)

    Returns:
        float 0.0–1.0
    """
    score = (
        WEIGHTS['ablation']    * ablation +
        WEIGHTS['replication'] * replication +
        WEIGHTS['transfer']    * transfer
    )
    return round(min(1.0, max(0.0, score)), 3)


def classify(score):
    """
    Map confidence score to classification label.

    Returns:
        str: 'strongly_causal' | 'likely_causal' | 'uncertain' | 'spurious'
    """
    if score >= THRESHOLDS['strongly_causal']:
        return 'strongly_causal'
    elif score >= THRESHOLDS['likely_causal']:
        return 'likely_causal'
    elif score >= THRESHOLDS['uncertain']:
        return 'uncertain'
    else:
        return 'spurious'


def get_emoji(classification):
    """Returns display emoji for classification."""
    return {
        'strongly_causal': '✓✓',
        'likely_causal':   '✓',
        'uncertain':       '?',
        'spurious':        '✗',
    }.get(classification, '?')
