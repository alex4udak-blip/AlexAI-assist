"""
Unified Confidence Calculation Utilities.
Provides consistent confidence calculation across all memory services.
"""

import math
from datetime import datetime


def calculate_reinforcement(
    current_confidence: float,
    reinforcement_strength: float = 0.2,
) -> float:
    """
    Increase confidence with diminishing returns.

    As confidence approaches 1.0, increases become smaller.
    This prevents overconfidence while allowing strong beliefs to strengthen.

    Args:
        current_confidence: Current confidence value (0.0-1.0)
        reinforcement_strength: How much to increase (0.0-1.0, default 0.2)

    Returns:
        New confidence value (0.0-1.0)

    Formula: current + (1 - current) * strength
    Example: 0.5 + (1 - 0.5) * 0.2 = 0.5 + 0.1 = 0.6
    """
    current_confidence = _clamp(current_confidence)
    reinforcement_strength = _clamp(reinforcement_strength, 0.0, 0.5)

    new_confidence = current_confidence + (1.0 - current_confidence) * reinforcement_strength
    return _clamp(new_confidence)


def calculate_challenge(
    current_confidence: float,
    challenge_strength: float = 0.7,
) -> float:
    """
    Decrease confidence proportionally.

    Reduces confidence by multiplying with a factor less than 1.
    Stronger challenges result in larger decreases.

    Args:
        current_confidence: Current confidence value (0.0-1.0)
        challenge_strength: Multiplier for decrease (0.0-1.0, default 0.7)
            Lower values = stronger challenge

    Returns:
        New confidence value (0.0-1.0)

    Formula: current * strength
    Example: 0.8 * 0.7 = 0.56
    """
    current_confidence = _clamp(current_confidence)
    challenge_strength = _clamp(challenge_strength, 0.0, 1.0)

    new_confidence = current_confidence * challenge_strength
    return _clamp(new_confidence, min_value=0.01)


def calculate_time_decay(
    current_confidence: float,
    last_reinforced: datetime,
    now: datetime | None = None,
    decay_rate: float = 0.01,
    min_confidence: float = 0.1,
) -> float:
    """
    Apply time-based decay to confidence.

    Confidence naturally decays over time if not reinforced.
    Decay is proportional to time passed and remaining confidence.

    Args:
        current_confidence: Current confidence value (0.0-1.0)
        last_reinforced: When the confidence was last increased
        now: Current time (defaults to utcnow)
        decay_rate: Daily decay rate (default 0.01 = 1% per day)
        min_confidence: Minimum confidence floor (default 0.1)

    Returns:
        New confidence value (0.0-1.0)

    Formula: current - (days_passed * decay_rate * (1 - current))
    This ensures higher confidence values decay slower (stability of strong beliefs).
    """
    if now is None:
        now = datetime.utcnow()

    current_confidence = _clamp(current_confidence)
    decay_rate = max(0.0, min(0.1, decay_rate))
    min_confidence = _clamp(min_confidence, 0.0, 0.5)

    # Calculate days since last reinforcement
    time_delta = now - last_reinforced
    days_passed = time_delta.total_seconds() / 86400  # seconds in a day

    # Decay amount is proportional to time and inversely proportional to confidence
    # Strong beliefs (high confidence) decay slower
    decay_amount = days_passed * decay_rate * (1.0 - current_confidence)
    new_confidence = current_confidence - decay_amount

    return _clamp(new_confidence, min_value=min_confidence)


def calculate_exponential_decay(
    current_confidence: float,
    hours_since_access: float,
    half_life_hours: float = 168.0,  # 1 week
) -> float:
    """
    Apply exponential decay based on time since last access.

    Uses exponential decay formula for more realistic forgetting curves.
    Suitable for heat scores and recency-based confidence.

    Args:
        current_confidence: Current confidence/heat value (0.0-2.0)
        hours_since_access: Hours since last access
        half_life_hours: Hours for value to decay to 50% (default 168 = 1 week)

    Returns:
        Decayed value

    Formula: current * exp(-hours / half_life)
    """
    current_confidence = max(0.0, current_confidence)
    hours_since_access = max(0.0, hours_since_access)
    half_life_hours = max(1.0, half_life_hours)

    decay_factor = math.exp(-hours_since_access / half_life_hours)
    new_value = current_confidence * decay_factor

    return max(0.0, new_value)


def calculate_weighted_average(
    old_confidence: float,
    new_confidence: float,
    old_weight: float = 0.7,
) -> float:
    """
    Calculate weighted average of old and new confidence.

    Useful when merging duplicate memories or averaging evidence.

    Args:
        old_confidence: Existing confidence value
        new_confidence: New evidence confidence
        old_weight: Weight for old value (0.0-1.0, default 0.7)

    Returns:
        Weighted average confidence (0.0-1.0)

    Formula: old * old_weight + new * (1 - old_weight)
    """
    old_confidence = _clamp(old_confidence)
    new_confidence = _clamp(new_confidence)
    old_weight = _clamp(old_weight)

    weighted = old_confidence * old_weight + new_confidence * (1.0 - old_weight)
    return _clamp(weighted)


def calculate_evidence_based_confidence(
    supporting_evidence_count: int,
    contradicting_evidence_count: int,
    base_confidence: float = 0.5,
) -> float:
    """
    Calculate confidence based on supporting vs contradicting evidence.

    Uses evidence ratio to adjust confidence from a base value.
    More supporting evidence increases confidence.
    More contradicting evidence decreases confidence.

    Args:
        supporting_evidence_count: Number of supporting facts
        contradicting_evidence_count: Number of contradicting facts
        base_confidence: Starting confidence (default 0.5)

    Returns:
        Evidence-adjusted confidence (0.0-1.0)
    """
    base_confidence = _clamp(base_confidence, 0.3, 0.7)

    total_evidence = supporting_evidence_count + contradicting_evidence_count
    if total_evidence == 0:
        return base_confidence

    # Calculate evidence ratio (-1 to 1)
    # -1 = all contradicting, 0 = balanced, 1 = all supporting
    evidence_ratio = (supporting_evidence_count - contradicting_evidence_count) / total_evidence

    # Adjust confidence based on ratio
    # Positive ratio increases confidence, negative decreases
    adjustment = evidence_ratio * (1.0 - base_confidence) * 0.5
    new_confidence = base_confidence + adjustment

    return _clamp(new_confidence)


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """
    Clamp value to range [min_value, max_value].

    Args:
        value: Value to clamp
        min_value: Minimum allowed value (default 0.0)
        max_value: Maximum allowed value (default 1.0)

    Returns:
        Clamped value
    """
    return max(min_value, min(max_value, value))
