# Phase 5H.11 — Generic Prospective Review and Decision

Phase 5H.11 provides the generic monitoring and research-decision layer for
reports that comply with the Phase 5H.10 prospective contract.

## Monitoring states

- `WAITING_FOR_CANDIDATE_SIGNAL`
- `WAITING_FOR_MATURITY`
- `ACCUMULATING_MATURED_SAMPLE`
- `REVIEW_REQUIRED`

The minimum matured sample comes from the frozen protocol generated in 5H.10.

## Research decisions

- `NOT_READY`
- `INCONCLUSIVE`
- `PASS_RESEARCH`
- `FAIL_RESEARCH`

After the minimum matured sample is reached, `PASS_RESEARCH` requires:

```text
average net return > 0
median net return > 0
positive return rate > 50%
uplift vs baseline > 0
historical integrity valid
frozen definition valid
```

Generic report validation establishes the integrity and frozen-definition gates
before review or decision output is produced.

## Phase 6 isolation

Even when the decision is `PASS_RESEARCH`:

```text
phase6_eligible = false
phase6_blocked = true
automatic_phase6_promotion = false
```

A separate human decision is required outside this protocol.

Existing XRP Phase 5G remains unchanged and continues to use its current 5G.2
and 5G.3 implementation.
