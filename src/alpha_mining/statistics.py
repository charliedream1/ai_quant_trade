"""Pre-registered date-block inference and familywise error correction."""

from typing import Any

import numpy as np

from .config import invalid


def block_test(values: list[float], policy: dict[str, Any]) -> dict[str, Any]:
    x = np.asarray(values, dtype=float)
    if not np.isfinite(x).all() or len(x) < policy["min_test_dates"]:
        return {"status": "insufficient", "samples": len(x), "p_value": 1.0, "mean": None, "interval": None}
    block = policy["block_sessions"]
    if len(x) < 2 * block:
        return {"status": "insufficient_blocks", "samples": len(x), "p_value": 1.0, "mean": None, "interval": None}
    rng = np.random.default_rng(policy["seed"])
    starts = rng.integers(0, len(x) - block + 1, size=(policy["bootstrap_samples"], int(np.ceil(len(x) / block))))
    indices = (starts[..., None] + np.arange(block)).reshape(policy["bootstrap_samples"], -1)[:, : len(x)]
    means = x[indices].mean(axis=1)
    center = float(x.mean())
    null_means = means - center
    p_value = float((1 + np.count_nonzero(null_means >= center)) / (len(means) + 1))
    if np.ptp(x) <= np.finfo(float).eps:
        p_value = 1.0
    alpha = policy["significance"]
    return {
        "status": "evaluated",
        "method": "one_sided_null_centered_moving_date_blocks",
        "samples": len(x),
        "block_sessions": block,
        "bootstrap_samples": len(means),
        "seed": policy["seed"],
        "mean": center,
        "p_value": p_value,
        "interval": np.quantile(means, [alpha / 2, 1 - alpha / 2]).tolist(),
    }


def holm(p_values: list[float], family_size: int) -> list[float]:
    if family_size < len(p_values) or family_size < 1:
        raise invalid("试验家族分母不能小于实际候选数量")
    if any(not np.isfinite(value) or not 0 <= value <= 1 for value in p_values):
        raise invalid("显著性数值不合法")
    output, previous = [1.0] * len(p_values), 0.0
    for rank, index in enumerate(sorted(range(len(p_values)), key=lambda i: (p_values[i], i))):
        previous = min(1.0, max(previous, p_values[index] * (family_size - rank)))
        output[index] = previous
    return output
