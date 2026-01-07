# Confidence Calculation Unification

## Overview

This document describes the unified confidence calculation system implemented across all memory services.

## Problem

Previously, different memory services used inconsistent formulas for confidence calculations:

1. **fact_network.py** - Used weighted average with bonus: `(old + new) / 2 + 0.1`
2. **belief_network.py** - Used multiple different formulas:
   - Reinforcement: `old + (1 - old) * 0.2` (diminishing returns)
   - Challenge: `old * 0.7` (proportional decrease)
   - Evolution: Various fixed adjustments
3. **memory_scheduler.py** - Used different decay formulas for facts and beliefs
4. **observation_network.py** - Used simple average: `(old + new) / 2`

## Solution

Created a unified `confidence_utils.py` module with standardized functions:

### Core Functions

1. **`calculate_reinforcement(current, strength=0.2)`**
   - Increases confidence with diminishing returns
   - Formula: `current + (1 - current) * strength`
   - Prevents overconfidence as values approach 1.0

2. **`calculate_challenge(current, strength=0.7)`**
   - Decreases confidence proportionally
   - Formula: `current * strength`
   - Maintains minimum confidence of 0.01

3. **`calculate_time_decay(current, last_reinforced, decay_rate=0.01)`**
   - Natural decay over time
   - Formula: `current - (days * decay_rate * (1 - current))`
   - Higher confidence values decay slower (stable beliefs)

4. **`calculate_weighted_average(old, new, old_weight=0.7)`**
   - Merges confidence values when combining memories
   - Formula: `old * old_weight + new * (1 - old_weight)`

5. **`calculate_exponential_decay(current, hours_since_access, half_life=168)`**
   - Exponential decay for heat scores
   - Formula: `current * exp(-hours / half_life)`

6. **`calculate_evidence_based_confidence(supporting, contradicting, base=0.5)`**
   - Adjusts confidence based on evidence ratio
   - Increases with supporting evidence, decreases with contradicting

### Supporting Features

- All functions clamp output to valid range (0.0-1.0)
- Type hints for all parameters
- Comprehensive docstrings with formulas and examples
- Validation of input ranges

## Updated Services

### 1. fact_network.py
- **Updated**: `_reinforce()` method
- **Before**: `(confidence + new_confidence) / 2 + 0.1`
- **After**: Uses `calculate_weighted_average()` then `calculate_reinforcement()`
- **Benefits**: Consistent with other services, no arbitrary bonus

### 2. belief_network.py
- **Updated**:
  - `reinforce()` method - uses `calculate_reinforcement()`
  - `challenge()` method - uses `calculate_challenge()`
  - `evolve_from_evidence()` method - uses both functions
- **Before**: Inline formulas with magic numbers
- **After**: Clear function calls with named parameters
- **Benefits**: Explicit intent, easier to tune parameters

### 3. memory_scheduler.py
- **Updated**:
  - Added `calculate_memory_decay()` method for individual calculations
  - Added import and documentation
- **Note**: Batch `apply_decay()` kept as SQL for performance
- **Benefits**: Individual decay calculations now use unified formula

### 4. observation_network.py
- **Updated**: Relationship confidence merging
- **Before**: Simple average `(old + new) / 2`
- **After**: `calculate_weighted_average(old, new, 0.5)`
- **Benefits**: Consistent with other merging operations, adjustable weights

## Usage Examples

```python
from src.services.memory.confidence_utils import (
    calculate_reinforcement,
    calculate_challenge,
    calculate_time_decay,
)

# Reinforce a belief after confirming evidence
new_confidence = calculate_reinforcement(
    current_confidence=0.7,
    reinforcement_strength=0.2  # 20% of remaining headroom
)
# Result: 0.7 + (1 - 0.7) * 0.2 = 0.76

# Challenge a belief with contradicting evidence
new_confidence = calculate_challenge(
    current_confidence=0.8,
    challenge_strength=0.7  # Reduce to 70% of current
)
# Result: 0.8 * 0.7 = 0.56

# Apply time-based decay (7 days, 1% daily rate)
new_confidence = calculate_time_decay(
    current_confidence=0.8,
    last_reinforced=datetime(2024, 1, 1),
    now=datetime(2024, 1, 8),
    decay_rate=0.01,
)
# Result: 0.8 - (7 * 0.01 * 0.2) ≈ 0.786
```

## Benefits

1. **Consistency**: All services use the same formulas for the same operations
2. **Maintainability**: Central location for confidence logic
3. **Testability**: Functions are pure and easy to unit test
4. **Tunability**: Parameters clearly documented and adjustable
5. **Understandability**: Named functions make intent clear

## Future Enhancements

Possible improvements:
- Add support for context-based decay rates (domain importance)
- Implement confidence calibration based on prediction accuracy
- Add statistical confidence intervals
- Support for Bayesian confidence updates

## Migration Notes

- All changes are backward compatible
- Existing confidence values remain valid
- New calculations may produce slightly different results but within acceptable range
- SQL batch operations maintained for performance
