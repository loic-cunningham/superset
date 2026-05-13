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

## Weak spot analysis

Pre-mutation coverage analysis identified these weak spots for targeted mutation design:
- {{weak_spot_1 — e.g., "bigquery.py:_information_schema_ref has 0% branch coverage on escaping paths"}}
- {{weak_spot_2 — e.g., "hive.py:df_to_sql LIKE escaping is covered but never asserted with special characters"}}
- {{weak_spot_3}}

Failure area coverage:
| Failure area | Applicable? | Mutations targeting it |
|---|---|---|
| Validation/guards | {{yes/no}} | {{M_ids or "n/a"}} |
| Data integrity | {{yes/no}} | {{M_ids or "n/a"}} |
| Error handling | {{yes/no}} | {{M_ids or "n/a"}} |
| Security boundaries | {{yes/no}} | {{M_ids or "n/a"}} |
| Control flow | {{yes/no}} | {{M_ids or "n/a"}} |
| Boundary conditions | {{yes/no}} | {{M_ids or "n/a"}} |
| Configuration/wiring | {{yes/no}} | {{M_ids or "n/a"}} |
| Output contracts | {{yes/no}} | {{M_ids or "n/a"}} |

## Initial mutation plan

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| M1 | {{file}} | {{description}} | {{category}} | {{high/medium/low}} | {{why this mutation targets an identified weak spot}} |
| M2 | {{file}} | {{description}} | {{category}} | {{high/medium/low}} | {{why this mutation targets an identified weak spot}} |

Gap/strength ratio: {{gap_count}}/{{total}} gap mutations ({{percent}}%)

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

## Mutation quality self-assessment

- Initial kill rate: {{percent}} — {{assessment: e.g., "mutations were well-targeted" if 50-80%, or "mutations could have been harder" if >80%}}
- Gap/strength ratio: {{gap_count}}/{{total}} ({{percent}}% gap)
- Failure areas covered: {{count}}/{{applicable_count}}
- Mutations informed by coverage analysis: {{count}}/{{total}}
```
