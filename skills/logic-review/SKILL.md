---
name: logic-review
description: Use when reviewing a plan, design, proposal, or idea for logical soundness. Invoke to check internal consistency, surface hidden assumptions, find counter-arguments, and verify that context and conclusions actually align.
---

# Logic Review

> **Rules (read first):** Never soften findings. Every Option needs gain + lose. Flag load-bearing issues first.

A structural audit for logical coherence. Not a style check — find where the logic breaks before committing.

## When to Use

- Before finalizing a design or architecture decision
- After writing a plan or proposal
- When something "feels off" but you can't name why
- When you want to stress-test your own reasoning

## Four Checks

Run all four before writing output.

**1. Internal Consistency** — Do stated goals match proposed actions? Do constraints conflict? Does A require B that isn't provided?

**2. Assumption Audit** — What must be true for this to work? Which assumptions are load-bearing? Which have no evidence?

**3. Context-Logic Alignment** — Does the solution address the real problem or a proxy? Would this logic only hold in a different context?

**4. Counter-Argument Search** — What's the strongest case against this? Under what conditions does it fail? What would a skeptic say?

## Review Format

```
## Logic Review

### Verdict
[SOUND / WEAK / BROKEN] — one sentence. If SOUND, say so — don't invent problems.

### Inconsistencies
<!-- Find: goal vs action mismatches, A-requires-B gaps, contradicting constraints -->
- [none] or [Claim A] conflicts with [Claim B] because [reason]

### Unvalidated Assumptions
<!-- Find: load-bearing assumptions with no evidence; what is conspicuously NOT mentioned -->
- [Assumption] | load-bearing: yes/no | evidence: yes/no

### Context Gaps
<!-- Find: logic that only holds in a different context; proxy problems -->
- [none] or list

### Counter-Arguments
<!-- Find: strongest objection, failure conditions, falsifying evidence — do not soften -->
1. [Strongest objection]
2. [Second objection]
3. [Third, if applicable]

### Recommendation

**Option A: [approach name]**
- What you gain: ...
- What you lose: ...

**Option B: [approach name]**
- What you gain: ...
- What you lose: ...
```

## Constraints

- Never soften findings — the user asked for this review
- If logic is sound, say so — don't invent problems
- Prioritize load-bearing weaknesses over cosmetic ones
- Every Option needs both gain and lose — no exceptions
