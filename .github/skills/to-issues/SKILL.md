---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

If present, read `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md` before publishing so you use the repo's configured tracker and label vocabulary.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an issue reference (issue number, URL, or path) as an argument, fetch it from the issue tracker and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- Keep slice size small: one behavior change plus at most one adapter touch unless trivial
- Prefer parser/input-normalization tracer bullets before computational logic bullets when sequencing early work
</vertical-slice-rules>

Core behavior policy for slicing:

- Any slice that changes baseline behavior in computational logic or parser/input normalization must be marked HITL.
- HITL core slices must require a behavior-delta review artifact and explicit human approval before merge.
- Non-core application-layer behavior changes may be opt-in-first where appropriate.

Initial CI trigger scope for core behavior artifacts:

- `hydropattern/patterns.py`
- `hydropattern/parsers.py`

Behavior-delta artifact convention for applicable slices:

- Folder: `docs/review/behavior-deltas/`
- Filename: `issue-<number>-<short-slug>.md`

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Publish the issues to the issue tracker

For each approved slice, publish a new issue to the issue tracker. Use the issue body template below and apply canonical triage labels:

- AFK slice: `ready-for-agent`
- HITL slice: `ready-for-human`

Publish issues in dependency order (blockers first) so you can reference real issue identifiers in the "Blocked by" field.

For core behavior-adjudication slices, keep `ready-for-human` until explicit human approval is recorded. After approval, if remaining work is autonomous, transition to `ready-for-agent`.

<issue-template>
## Parent

A reference to the parent issue on the issue tracker (if the source was an existing issue, otherwise omit this section).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

Avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it here and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

If the slice changes core computational/parser behavior, include these explicit criteria:

- [ ] Behavior Delta Report included: changed behavior, winner determination with rationale, before/after example, risks, and proving tests
- [ ] Behavior Delta Report artifact added using the required path/filename convention
- [ ] Affected code locations are clearly identified
- [ ] Human approval obtained before merge

## Blocked by

- A reference to the blocking ticket (if any)

Or "None - can start immediately" if no blockers.

</issue-template>

Do NOT close or modify any parent issue.
