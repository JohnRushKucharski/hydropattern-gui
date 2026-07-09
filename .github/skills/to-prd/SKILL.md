---
name: to-prd
description: Turn the current conversation context into a PRD and publish it to the project issue tracker. Use when user wants to create a PRD from the current context.
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

If present, read `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md` before publishing so you use the repo's configured tracker and label vocabulary.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the PRD, and respect any ADRs in the area you're touching.

2. Sketch out the major modules you will need to build or modify to complete the implementation. Actively look for opportunities to extract deep modules that can be tested in isolation.

A deep module (as opposed to a shallow module) is one which encapsulates a lot of functionality in a simple, testable interface which rarely changes.

Check with the user that these modules match their expectations. Check with the user which modules they want tests written for.

2a. When the context is a reorganization or merge-back program, structure the PRD set as:

- One umbrella PRD for overall outcomes and governance.
- Child PRDs by concern area, using vertical tracer-bullet execution at issue level.
- If core scope is substantial, split core into computational logic and parsing/input normalization.

2b. Capture mandatory governance decisions in the PRD (when present in context):

- Shared application service layer used by CLI, GUI, and notebook/library workflows.
- Core behavior-change adjudication policy (hydropattern intent first, then reproducible test evidence).
- Core behavior-change review policy: one-by-one human approval with a behavior delta summary and affected code pointers.
- Merge gates: required tests, no new lint/type warnings or errors, and required artifacts.
- Tracer-bullet slice size and definition-of-done constraints.
- Branching model: short-lived issue branches, one branch per issue.
- Pre-1.0 release model: frequent minor releases with explicit changelog and migration notes for breaking changes.
- CI enforcement model: path-based triggers for core behavior-change artifacts, PR template requirements, and artifact-file conventions.

2c. PRD readiness gate:

- A PRD may be drafted/published only when its own blocking decisions are locked.
- Unresolved items may be recorded as "Assumption Pending" only if they are non-blocking for that PRD.
- If blocking items remain unresolved, mark the PRD status as "Draft-Blocked" and do not convert it into implementation issues yet.

3. Write the PRD using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label - no need for additional triage.

<prd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Also include:

- Explicit non-goals for this PRD to prevent scope bleed into sibling PRDs.
- Decision Log entries for locked governance decisions relevant to this PRD (status and date).

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

If present in context, also include:

- Cross-workflow parity expectations (library/API, CLI, GUI) for touched behavior.
- Required behavior-delta evidence for core computational/parser changes.
- Pre-commit quality review checklist themes: architecture integrity, module depth/locality, SOLID/DRY with judgment, complexity control, and adapter thinness.

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</prd-template>
