# Decision Journal Idempotence Rules

## Decision ID Format

```
dec_{cycle_id}_{symbol}_{deterministic_hash}
```

Where `deterministic_hash` is a 16-character hex SHA-1 hash of the record's essential fields.

## When a Decision ID is Stable (Idempotent)

A decision ID remains **unchanged** across retries, restarts, and concurrent calls when:

1. **Same cycle_id** - The logical trading cycle identifier
2. **Same symbol** - Trading pair (e.g., BTCUSDT)
3. **Same action** - BUY, SELL, or REDUCE
4. **Same eligibility** - PAPER_PROPOSAL, RESEARCH_ONLY, BLOCKED
5. **Same confidence_score** - Float value
6. **Same heuristic_score** - Float value
7. **Same max_notional_usd** - Position size limit
8. **Same entry_plan** - If present: side, symbol, entry_price
9. **Same sizing_details_json** - If present: sizing configuration

## When a New Decision ID is Generated

A **new** decision ID is generated when ANY of these fields change:

- Symbol changes (BTCUSDT → ETHUSDT)
- Action changes (BUY → SELL)
- Eligibility changes (PAPER_PROPOSAL → RESEARCH_ONLY)
- Cycle ID changes (manual override for reprocessing)
- Confidence score differs
- Heuristic score differs
- Max notional differs
- Entry plan parameters differ

## Idempotency Guarantees

### Retry Scenarios
- Same logical decision executed twice produces the same `decision_id`
- Journal performs lookup before insert (upsert pattern)
- Prevents duplicate position entries

### Restart Scenarios
- After process crash/restart, same input produces same ID
- Allows recovery and audit trail continuity
- Hash-based ID survives timestamp changes

### Concurrency
- Deterministic hash allows parallel workers to generate identical IDs
- Database-level unique constraint prevents duplicates
- Applications should use `ON CONFLICT` or equivalent upserts

## Hash Generation Algorithm

```python
def _decision_id_hash(cycle_id, record):
    hash_input = f"{cycle_id}:{record.symbol}:{record.action.value}:
                   {record.eligibility.value}:{record.confidence_score}:
                   {record.heuristic_score}:{record.max_notional_usd}"
    if record.entry_plan:
        hash_input += f":{record.entry_plan.side.value}:
                       {record.entry_plan.symbol}:
                       {record.entry_plan.entry_price}"
    if record.sizing_details_json:
        hash_input += f":{record.sizing_details_json}"
    return sha1(hash_input.encode("utf-8")).hexdigest()[:16]
```

## Outcome Linking

Outcomes are linked to decisions via `decision_id`. The `record_outcome` method:
1. Checks if outcome (decision_id + order_id) already exists
2. Only appends if not already recorded
3. Maintains idempotent write for fill events

## Supabase Storage

The `decision_journal` table uses `decision_id` as the primary identifier. No migration required - the new format maintains compatibility with existing schema.