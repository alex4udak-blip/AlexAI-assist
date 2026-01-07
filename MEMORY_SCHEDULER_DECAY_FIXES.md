# Memory Scheduler Decay Logic Fixes

## Summary
Fixed critical issues in the memory scheduler decay logic in `/home/user/AlexAI-assist/apps/server/src/services/memory/memory_scheduler.py`.

## Issues Fixed

### 1. DECAY_RATE Constants Not Used
**Problem:** Three decay rate constants (`DECAY_RATE_FAST`, `DECAY_RATE_NORMAL`, `DECAY_RATE_SLOW`) were defined but never used.

**Solution:**
- Added `get_decay_rate_for_type()` method that returns appropriate decay rates based on memory type and importance
- Updated documentation to clarify decay rates correspond to different half-lives (1 week, 2 weeks, 4 weeks)
- The existing `calculate_memory_decay()` method now properly uses these constants

### 2. Inconsistent Decay Calculation in apply_decay()
**Problem:** The `apply_decay()` method was trying to use `heat_score - decay_rate` where `decay_rate` is a column that only exists in `memory_facts` table, not in other memory tables.

**Solution:**
- Replaced simple subtraction with proper exponential time-based decay formula
- For facts: `heat_score * EXP(-time_elapsed / (168 * 3600))` (1 week half-life)
- For beliefs: `confidence * EXP(-time_elapsed / (672 * 3600))` (4 week half-life)
- Decay is now based on time since last access (facts) or last reinforcement (beliefs)
- Added condition to only decay memories older than 1 hour (facts) or 7 days (beliefs)
- Heat scores properly bounded with `GREATEST(0.0, ...)` to prevent negative values

### 3. Heat Score Updates Don't Apply Decay Properly
**Problem:** `update_heat_scores()` was just adding 0.2 to the heat score without considering time-based decay since last access.

**Solution:**
- Modified to apply exponential time-based decay BEFORE adding boost
- Uses formula: `heat_score * EXP(-time_since_last_access / (168 * 3600)) + 0.2`
- Falls back to using `created_at` if `last_accessed` is NULL
- Properly bounded with `LEAST(2.0, GREATEST(0.0, ...))` to keep scores in valid range [0.0, 2.0]
- Now correctly reflects memory recency in addition to access frequency
- **Performance optimization:** Groups operations by table for batch processing using `ANY(:memory_ids)`

## Key Improvements

### Time-Based Decay
All decay calculations now use exponential decay based on elapsed time:
- **Exponential formula:** `value * EXP(-elapsed_time / half_life)`
- **Week half-life for facts:** 168 hours (7 days)
- **4-week half-life for beliefs:** 672 hours (28 days)

### Memory Type Differentiation
Different memory types now have different decay characteristics:
- **Facts:** Normal decay (1 week half-life), can vary based on importance
- **Beliefs:** Slow decay (4 week half-life) - represents stable knowledge
- **Experiences:** Normal decay (configurable)
- **Entities:** Slow decay (configurable)

### Bounded Heat Scores
All heat score updates ensure scores remain in valid range [0.0, 2.0]:
- Lower bound: `GREATEST(0.0, ...)` prevents negative heat scores
- Upper bound: `LEAST(2.0, ...)` prevents excessive heat scores

### Null Safety
All SQL queries handle NULL timestamps gracefully:
- Uses `COALESCE(last_accessed, created_at)` for facts
- Uses `COALESCE(last_reinforced, formed_at)` for beliefs
- Uses `COALESCE(access_count, 0)` for counter updates

## Methods Modified

### 1. `get_decay_rate_for_type()` [NEW]
```python
def get_decay_rate_for_type(self, memory_type: str, importance: float = 1.0) -> float
```
- Returns appropriate decay rate for memory type and importance level
- Used by `calculate_memory_decay()` for individual memory calculations

### 2. `update_heat_scores()`
- Now applies time-based decay before adding boost
- Properly handles NULL timestamps
- Ensures heat scores stay in [0.0, 2.0] range
- Groups operations by table for batch updates (uses `ANY(:memory_ids)` for performance)

### 3. `apply_decay()`
- Uses proper exponential time-based decay formula
- Different decay rates for facts vs beliefs
- Only decays memories that haven't been accessed recently
- Properly bounded to prevent negative values

## Testing Recommendations

1. **Unit Tests:**
   - Test `get_decay_rate_for_type()` with different memory types and importance levels
   - Test heat score bounds (verify 0.0 <= heat_score <= 2.0)
   - Test decay over different time periods

2. **Integration Tests:**
   - Verify `apply_decay()` correctly updates multiple memories
   - Test `update_heat_scores()` with various time gaps
   - Verify beliefs decay slower than facts

3. **Performance Tests:**
   - Test batch decay performance with large numbers of memories
   - Verify SQL queries use proper indexes (heat_score, last_accessed, session_id)

## Database Schema Notes

The fixes assume the following columns exist:
- **memory_facts:** id, session_id, heat_score, access_count, last_accessed, created_at, decay_rate
- **memory_beliefs:** id, session_id, confidence, status, last_reinforced, formed_at

The `decay_rate` column in `memory_facts` table is still available for per-memory customization but is no longer required for the decay calculation to work.

## Related Files

Files that call these methods:
- `/home/user/AlexAI-assist/apps/server/src/services/memory/memory_manager.py`
  - Calls `update_heat_scores()` after memory operations
  - Calls `apply_decay()` during maintenance
- `/home/user/AlexAI-assist/apps/server/src/core/scheduler.py`
  - Calls `apply_decay()` as scheduled background job

No changes needed in these files - the API remains the same.
