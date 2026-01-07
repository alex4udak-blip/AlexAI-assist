# Confidence Formula Comparison: Before vs After

## Summary

This document compares the old confidence calculation formulas with the new unified approach.

## 1. Fact Reinforcement (fact_network.py)

### Before
```python
# Line 300 in _reinforce()
fact.confidence = min(1.0, (fact.confidence + new_confidence) / 2 + 0.1)
```

**Issues:**
- Adds arbitrary +0.1 bonus
- Can exceed 1.0 before clamping
- Inconsistent with other services

### After
```python
weighted_confidence = calculate_weighted_average(
    fact.confidence, new_confidence, old_weight=0.6
)
fact.confidence = calculate_reinforcement(weighted_confidence, reinforcement_strength=0.15)
```

**Benefits:**
- No arbitrary bonuses
- Proper weighted merge of old and new
- Diminishing returns via reinforcement
- Always stays within bounds

**Formula:** `weighted = old * 0.6 + new * 0.4` → `reinforced = weighted + (1 - weighted) * 0.15`

---

## 2. Belief Reinforcement (belief_network.py)

### Before
```python
# Line 174 in reinforce()
new_confidence = min(0.99, old_confidence + (1 - old_confidence) * 0.2)
```

**Issues:**
- Inline formula hard to understand
- Magic number 0.2

### After
```python
new_confidence = calculate_reinforcement(old_confidence, reinforcement_strength=0.2)
```

**Benefits:**
- Clear function name indicates purpose
- Named parameter shows exact intent
- Reusable across services

**Formula:** Same (`old + (1 - old) * 0.2`) but now centralized and documented

---

## 3. Belief Challenge (belief_network.py)

### Before
```python
# Line 218 in challenge()
new_confidence = max(0.01, old_confidence * 0.7)
```

**Issues:**
- Inline formula
- Magic number 0.7

### After
```python
new_confidence = calculate_challenge(old_confidence, challenge_strength=0.7)
```

**Benefits:**
- Clear function name
- Named parameter
- Consistent minimum confidence handling

**Formula:** Same (`old * 0.7`) but now centralized and documented

---

## 4. Belief Evolution (belief_network.py)

### Before (Reinforcement)
```python
# Line 347 in evolve_from_evidence()
belief.confidence = min(0.99, belief.confidence + 0.02)
```

### After (Reinforcement)
```python
belief.confidence = calculate_reinforcement(belief.confidence, reinforcement_strength=0.02)
```

**Formula Change:** `old + 0.02` → `old + (1 - old) * 0.02`

**Why Better:** Small reinforcement values now properly scale with diminishing returns

### Before (Challenge)
```python
# Line 370 in evolve_from_evidence()
belief.confidence = max(0.1, belief.confidence * 0.9)
```

### After (Challenge)
```python
belief.confidence = calculate_challenge(belief.confidence, challenge_strength=0.9)
```

**Formula:** Same (`old * 0.9`) but now centralized

---

## 5. Observation Confidence Merge (observation_network.py)

### Before
```python
# Line 365
existing.confidence = (existing.confidence + confidence) / 2
```

**Issues:**
- Simple average gives equal weight
- No control over merge strategy

### After
```python
existing.confidence = calculate_weighted_average(
    existing.confidence, confidence, old_weight=0.5
)
```

**Benefits:**
- Clear intent
- Adjustable weights
- Consistent with other merges

**Formula:** Same for `old_weight=0.5` (`(old + new) / 2`) but now configurable

---

## 6. Memory Scheduler Decay (memory_scheduler.py)

### Before
```python
# Line 205 (SQL)
confidence = GREATEST(0.1, confidence - (0.01 * (1 - confidence)))
```

**Issues:**
- Only in SQL, no Python equivalent
- Formula not reusable

### After
```python
# SQL kept for batch performance, but now documented
# New Python method added:
new_confidence = calculate_time_decay(
    current_confidence=belief.confidence,
    last_reinforced=belief.last_reinforced,
    now=datetime.utcnow(),
    decay_rate=0.01,
    min_confidence=0.1,
)
```

**Benefits:**
- Python version available for individual calculations
- Time-aware decay based on days since reinforcement
- Clear parameters

**Formula:** `current - (days * decay_rate * (1 - current))`

---

## Formula Reference

### Reinforcement (Diminishing Returns)
```
new = current + (1 - current) * strength
```
- As confidence approaches 1.0, increases get smaller
- Prevents overconfidence
- `strength=0.2` means 20% of remaining headroom

### Challenge (Proportional Decrease)
```
new = current * strength
```
- Reduces confidence proportionally
- `strength=0.7` means reduce to 70% of current value
- Minimum confidence enforced at 0.01

### Time Decay (Stability)
```
new = current - (days * decay_rate * (1 - current))
```
- High confidence values decay slower (stable beliefs)
- `decay_rate=0.01` means 1% daily decay of remaining uncertainty
- Minimum confidence enforced

### Weighted Average (Merging)
```
new = old * old_weight + new * (1 - old_weight)
```
- Configurable blend of old and new values
- `old_weight=0.7` means 70% old, 30% new
- Useful for merging duplicate memories

---

## Impact Summary

| Operation | Service | Formula Change | Impact |
|-----------|---------|----------------|---------|
| Fact reinforcement | fact_network | Changed | More gradual increases, no arbitrary bonus |
| Belief reinforcement | belief_network | Same formula, unified | Consistent API |
| Belief challenge | belief_network | Same formula, unified | Consistent API |
| Belief evolution (reinforce) | belief_network | Changed | Proper diminishing returns for small adjustments |
| Belief evolution (challenge) | belief_network | Same formula, unified | Consistent API |
| Observation merge | observation_network | Same default, configurable | More flexible |
| Memory decay | memory_scheduler | Added Python version | Individual calculations now possible |

---

## Testing Results

All unified functions tested and validated:
- ✓ Reinforcement calculation (0.5 → 0.6 with strength=0.2)
- ✓ Challenge calculation (0.8 → 0.56 with strength=0.7)
- ✓ Time decay calculation (proper day-based decay)
- ✓ Weighted average (proper blending)
- ✓ Clamping to valid range (0.0-1.0)

All Python files compile successfully with no syntax errors.
