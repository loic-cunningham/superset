# Template: Mutation Testing Log (Stage 2)

This template defines the structure for the repo-tracked mutation testing log file created during the Log phase (Phase 4) and updated through the end of the run.

File location: `.devin/mutation-testing/pr-<PR_NUMBER>-<YYYY-MM-DD>-<short-slug>.md`

---

## YAML front matter schema

```yaml
---
pr_id: {{pr_number}}
pr_title: "{{pr_title}}"
run_date: "{{YYYY-MM-DD}}"
agent: "devin"
repo: "{{owner/repo}}"
branch: "{{pr_branch}}"
base_branch: "{{base_branch}}"
mode: "mutation-testing-and-test-improvement"
status: "{{in_progress|completed}}"

triage:
  coverage_level: "{{absent|very_low|moderate|good}}"
  foundation_needed: {{true|false}}
  deselected_tests:
    - test_id: "{{test_id}}"
      reason: "{{pre-existing failure unrelated to PR}}"

target:
  behavior:
    - "{{critical_guarantee_1}}"
    - "{{critical_guarantee_2}}"
  implementation_files:
    - "{{path/to/impl_file_1}}"
    - "{{path/to/impl_file_2}}"
  test_files:
    - "{{path/to/test_file_1}}"
    - "{{path/to/test_file_2}}"

initial_state:
  targeted_tests:
    command: "pytest {{targeted test paths}} -q"
    passed: {{count}}
    failed: {{count}}
  coverage:
    line:
      percent: {{number}}
      covered: {{number}}
      total: {{number}}
    branch:
      percent: {{number}}
      covered: {{number}}
      total: {{number}}
  mutation_testing:
    valid_mutations: {{count}}
    killed: {{count}}
    survived: {{count}}
    kill_rate: {{percent}}

final_state:
  targeted_tests:
    command: "pytest {{targeted test paths}} -q"
    passed: {{count}}
    failed: {{count}}
  coverage:
    line:
      percent: {{number}}
      covered: {{number}}
      total: {{number}}
    branch:
      percent: {{number}}
      covered: {{number}}
      total: {{number}}
  mutation_testing:
    valid_mutations: {{count}}
    killed: {{count}}
    survived: {{count}}
    kill_rate: {{percent}}
    rerun_type: "{{full|survivor_focused}}"

commits:
  - "{{commit_sha}}"

artifacts:
  pr_comment_url: "{{url}}"
---
```

## Log body structure

```md
# Mutation Testing Log — PR #{{pr_id}}

## PR understanding

Behavior changed:
- {{behavior_1}}
- {{behavior_2}}

Critical guarantees:
- {{guarantee_1}}
- {{guarantee_2}}

Relevant implementation files:
- {{impl_file_1}}
- {{impl_file_2}}

Relevant tests:
- {{test_file_1}}
- {{test_file_2}}

Likely risk areas:
- {{risk_1}}
- {{risk_2}}

## Triage decision

Coverage level: {{absent|very_low|moderate|good}}
Foundation needed: {{yes/no}}
Deselected tests: {{list or "none"}}
Reason: {{triage_reasoning}}

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| {{file_1}} | {{pct}} | {{pct}} | {{n}}/{{total}} |
| {{file_2}} | {{pct}} | {{pct}} | {{n}}/{{total}} |
| **TOTAL** | **{{pct}}** | **{{pct}}** | **{{n}}/{{total}}** |

Uncovered PR-changed lines:
- {{file:line_range — description}}

## Initial mutation plan

| ID | File | Mutation | Category | Expected |
|---|---|---|---|---|
| M1 | {{file}} | {{description}} | {{category}} | {{strength/gap}} |
| M2 | {{file}} | {{description}} | {{category}} | {{strength/gap}} |

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | {{description}} | {{killed/survived/invalid}} | {{test_name or —}} |
| M2 | {{description}} | {{killed/survived/invalid}} | {{test_name or —}} |

Kill rate: {{killed}}/{{valid}} ({{percent}})

## Fix plan

### Mutation gap fixes
- {{surviving_mutation}} → {{planned_test}}

### Coverage gap fixes
- {{uncovered_lines}} → {{planned_test}}

### Behavioral gap fixes
- {{missing_edge_case}} → {{planned_test}}

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| {{test_file}} | Added `{{test_name}}` | {{M_ids or coverage description}} |

## Final verification

Targeted suite: {{passed}} passed, {{failed}} failed
Line coverage: {{percent}} ({{covered}}/{{total}})
Branch coverage: {{percent}} ({{covered}}/{{total}})
Kill rate: {{killed}}/{{valid}} ({{percent}}) — {{full|survivor_focused}} rerun

## Final assessment

{{Brief summary of initial findings, what was fixed, and final state.}}

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| {{area_1}} | {{test_description}} | {{reason}} |
| {{area_2}} | {{test_description}} | {{reason}} |

These are coverage opportunities identified from term-missing output and behavioral analysis, not just surviving mutations.
```
