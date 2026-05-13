---
pr_id: 30
pr_title: "fix(rls): prevent double-apply when converting physical dataset to virtual"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "feat/rls-fix-39725"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "moderate"
  foundation_needed: false
  deselected_tests: []

target:
  behavior:
    - "When apply_rls is called with exclude_dataset_id, the dataset with that id is excluded from RLS lookup for its own inner SQL."
    - "When get_predicates_for_table receives exclude_dataset_id, an extra SqlaTable.id != exclude_dataset_id filter is appended to the lookup."
    - "When collect_rls_predicates_for_sql is called for a virtual dataset cache key, exclude_dataset_id is propagated to get_predicates_for_table."
    - "SqlaTable.get_extra_cache_keys passes self.id as exclude_dataset_id when collecting RLS predicates for the virtual dataset's cache key."
    - "ExploreMixin._get_from_clause passes getattr(self, 'id', None) as exclude_dataset_id when applying RLS to virtual dataset inner SQL."
  implementation_files:
    - "superset/utils/rls.py"
    - "superset/connectors/sqla/models.py"
    - "superset/models/helpers.py"
  test_files:
    - "tests/unit_tests/sql_lab_test.py"
    - "tests/unit_tests/security/guest_rls_test.py"
    - "tests/unit_tests/models/test_virtual_dataset_format.py"
    - "tests/unit_tests/models/test_double_rls_virtual_dataset.py"

initial_state:
  targeted_tests:
    command: "pytest tests/unit_tests/sql_lab_test.py tests/unit_tests/security/guest_rls_test.py tests/unit_tests/models/test_virtual_dataset_format.py tests/unit_tests/models/test_double_rls_virtual_dataset.py -q"
    passed: 29
    failed: 0
  coverage:
    line:
      percent: 79
      covered: 27
      total: 35
    branch:
      percent: 88
      covered: 7
      total: 8
  mutation_testing:
    valid_mutations: 10
    killed: 3
    survived: 7
    kill_rate: 30

final_state:
  targeted_tests:
    command: "pytest tests/unit_tests/sql_lab_test.py tests/unit_tests/security/guest_rls_test.py tests/unit_tests/models/test_virtual_dataset_format.py tests/unit_tests/models/test_double_rls_virtual_dataset.py -q"
    passed: 33
    failed: 0
  coverage:
    line:
      percent: 93
      covered: 33
      total: 35
    branch:
      percent: 88
      covered: 7
      total: 8
  mutation_testing:
    valid_mutations: 10
    killed: 10
    survived: 0
    kill_rate: 100
    rerun_type: "full"

commits: []

artifacts:
  pr_comment_url: "https://github.com/loic-cunningham/superset/pull/30#issuecomment-4437247589"
---

# Mutation Testing Log — PR #30

## PR understanding

Behavior changed:
- `apply_rls()` / `get_predicates_for_table()` / `collect_rls_predicates_for_sql()` accept a new `exclude_dataset_id: int | None = None` parameter.
- When `exclude_dataset_id` is not `None`, the dataset lookup query inside `get_predicates_for_table` gains an extra `SqlaTable.id != exclude_dataset_id` filter so a virtual dataset's own row never matches when scanning its own inner SQL.
- `SqlaTable.get_extra_cache_keys` (in `superset/connectors/sqla/models.py`) now passes `exclude_dataset_id=self.id` when collecting RLS predicates for virtual dataset cache-key construction.
- `ExploreMixin._get_from_clause` (in `superset/models/helpers.py`) reads `self_id = getattr(self, "id", None)` and propagates it via `exclude_dataset_id=self_id` into `apply_rls` for every parsed statement in a virtual dataset's inner SQL.

Critical guarantees:
- A virtual dataset whose `table_name` happens to equal a table referenced inside its own SQL (e.g., after converting a physical dataset to virtual) does not double-apply its own RLS — once on the outer `WHERE` clause, once on the inner SQL.
- The exclusion is keyed by `SqlaTable.id`, not by `table_name`, so legitimately distinct datasets sharing a `table_name` keep their RLS.
- Non-dataset `ExploreMixin` subclasses (e.g. SQL Lab `Query`, which has no `id` attribute) must not raise — the `getattr(self, "id", None)` fallback returns `None`, and propagation degrades cleanly to the pre-fix behaviour.
- Cache key composition for a virtual dataset is consistent with what is actually applied at query time: both go through `collect_rls_predicates_for_sql` / `apply_rls` with the same `exclude_dataset_id`.

Relevant implementation files:
- `superset/utils/rls.py`
- `superset/connectors/sqla/models.py`
- `superset/models/helpers.py`

Relevant tests:
- `tests/unit_tests/sql_lab_test.py`
- `tests/unit_tests/security/guest_rls_test.py`
- `tests/unit_tests/models/test_virtual_dataset_format.py`
- `tests/unit_tests/models/test_double_rls_virtual_dataset.py`

Likely risk areas:
- The hero `SqlaTable.id != exclude_dataset_id` filter is asserted by clause count only (`len(and_clause.clauses) == 5`) — operator and operand mutations slip through.
- Propagation of `exclude_dataset_id` through `apply_rls` / `collect_rls_predicates_for_sql` and through both call sites (`SqlaTable.get_extra_cache_keys`, `ExploreMixin._get_from_clause`) is not asserted with a non-None value.
- `and_(*filters)` vs `or_(*filters)` in `get_predicates_for_table` is invisible to existing assertions.

## Triage decision

Coverage level: moderate (79% line / 88% branch on `superset/utils/rls.py`).
Foundation needed: no — coverage is well above the 30% Foundation threshold; the test suite collects and runs cleanly.
Deselected tests: none.
Reason: existing tests exercise the happy path; gaps are concentrated on operator/operand/propagation assertions for the new `exclude_dataset_id` plumbing, which is exactly what mutation testing is meant to surface.

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| superset/utils/rls.py | 79% | 88% | 27/35 |
| **TOTAL** | **79%** | **88%** | **27/35** |

Uncovered PR-changed lines:
- `superset/utils/rls.py:161-186` — body of `collect_rls_predicates_for_sql` (SQLScript parse path, `default_catalog` derivation, except branch). Tested indirectly via `SqlaTable.get_extra_cache_keys` integration only.

## Weak spot analysis

Pre-mutation coverage analysis identified these weak spots for targeted mutation design:
- `superset/utils/rls.py:109-110` — the new exclusion filter (`if exclude_dataset_id is not None: filters.append(SqlaTable.id != exclude_dataset_id)`) is verified only via clause-count, leaving operator (`!=`/`==`) and operand (`SqlaTable.id` / `exclude_dataset_id`) mutations undetected.
- `superset/utils/rls.py:64,179` — wrapper functions (`apply_rls`, `collect_rls_predicates_for_sql`) pass `exclude_dataset_id` to `get_predicates_for_table`. Existing tests only call the wrappers with the default `None`, so propagation of a non-None value is not asserted.
- `superset/connectors/sqla/models.py:2075` and `superset/models/helpers.py:2073` — the two call sites that originate the `exclude_dataset_id` propagation have no direct assertion in the targeted suite.
- `superset/models/helpers.py:2066` — `self_id = getattr(self, "id", None)` is the only path that keeps the code safe for non-dataset `ExploreMixin` subclasses; flipping it to `self.id` is silent against the current suite (depends on the mock having an `id` attribute).
- `superset/utils/rls.py:112` — `and_(*filters)` vs `or_(*filters)` materially changes lookup semantics but is invisible to clause-count assertions.

Failure area coverage:
| Failure area | Applicable? | Mutations targeting it |
|---|---|---|
| Validation/guards | yes | M3 |
| Data integrity | yes | M1, M2, M10 |
| Error handling | no | n/a |
| Security boundaries | yes | M1, M9 |
| Control flow | yes | M3, M8 |
| Boundary conditions | yes | M2 |
| Configuration/wiring | yes | M4, M5, M6, M7 |
| Output contracts | yes | M10 |

## Initial mutation plan

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| M1 | superset/utils/rls.py | `SqlaTable.id != exclude_dataset_id` → `SqlaTable.id == exclude_dataset_id` | gap (hero) | high | Inverts the exclusion semantics; clause-count assertion misses the operator flip. |
| M2 | superset/utils/rls.py | `SqlaTable.id != exclude_dataset_id` → `SqlaTable.id != 0` | gap | high | Hardcodes the exclusion operand; lookup excludes "dataset id 0" forever instead of the passed-in id. |
| M3 | superset/utils/rls.py | `if exclude_dataset_id is not None:` → `if exclude_dataset_id is None:` | strength | high | Inverts the guard; new `test_get_predicates_for_table_excludes_self` should catch this via clause-count. |
| M4 | superset/utils/rls.py | `exclude_dataset_id=exclude_dataset_id` in `apply_rls` → `exclude_dataset_id=None` | gap | high | Strips propagation through `apply_rls`; existing test only asserts the default value, so a non-None propagation test is needed. |
| M5 | superset/utils/rls.py | `exclude_dataset_id=exclude_dataset_id` in `collect_rls_predicates_for_sql` → `exclude_dataset_id=None` | gap | high | Same propagation pattern at the cache-key wrapper; not exercised directly in the targeted suite. |
| M6 | superset/connectors/sqla/models.py | `exclude_dataset_id=self.id` at `SqlaTable.get_extra_cache_keys` → `exclude_dataset_id=None` | gap | high | Originating call site for cache-key construction; survives because no test exercises it with `self.id` propagation. |
| M7 | superset/models/helpers.py | `exclude_dataset_id=self_id` at `ExploreMixin._get_from_clause` → `exclude_dataset_id=None` | gap | high | Originating call site for inner-SQL RLS; survives because the existing mock-based test patches `apply_rls` and doesn't assert kwargs. |
| M8 | superset/models/helpers.py | `self_id = getattr(self, "id", None)` → `self_id = self.id` | gap | medium | Breaks non-dataset `ExploreMixin` subclasses; strength test `test_sql_reformatted_when_rls_applied` happens to catch it via mocked `id`. |
| M9 | superset/utils/rls.py | `include_global_guest_rls=False` → `include_global_guest_rls=True` | strength | high | Existing guest-RLS tests assert the False keyword; should catch the flip. |
| M10 | superset/utils/rls.py | `and_(*filters)` → `or_(*filters)` | gap | high | Inverts lookup semantics from "all filters required" to "any filter sufficient"; clause-count assertion can't distinguish. |

Gap/strength ratio: 8/10 gap mutations (80%).

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | `SqlaTable.id != exclude_dataset_id` → `==` | survived | — |
| M2 | `SqlaTable.id != exclude_dataset_id` → `!= 0` | survived | — |
| M3 | `if exclude_dataset_id is not None:` → `is None:` | killed | tests/unit_tests/sql_lab_test.py::test_get_predicates_for_table_excludes_self |
| M4 | `apply_rls` propagation → `None` | survived | — |
| M5 | `collect_rls_predicates_for_sql` propagation → `None` | survived | — |
| M6 | `SqlaTable.get_extra_cache_keys` call site → `None` | survived | — |
| M7 | `ExploreMixin._get_from_clause` call site → `None` | survived | — |
| M8 | `self_id = getattr(self, "id", None)` → `self.id` | killed | tests/unit_tests/models/test_virtual_dataset_format.py::TestVirtualDatasetWithRLS::test_sql_reformatted_when_rls_applied |
| M9 | `include_global_guest_rls=False` → `True` | killed | tests/unit_tests/sql_lab_test.py::test_get_predicates_for_table |
| M10 | `and_(*filters)` → `or_(*filters)` | survived | — |

Kill rate: 3/10 (30%)

## Fix plan

### Mutation gap fixes
- M1: Add an assertion in `test_get_predicates_for_table_excludes_self` that inspects the exclusion clause directly (`operator == operators.ne`, `left.key == "id"`, `right.value == 42`) instead of only counting clauses.
- M2: Covered by the same direct-clause assertion (right operand check).
- M4: Add a new test `test_apply_rls_propagates_exclude_dataset_id` that calls `apply_rls(..., exclude_dataset_id=42)` and asserts `get_predicates_for_table` was called with `exclude_dataset_id=42`.
- M5: Add a new test `test_collect_rls_predicates_for_sql_propagates_exclude_dataset_id` that calls the collector with `exclude_dataset_id=42` and asserts the same propagation.
- M6: Add a test `test_get_extra_cache_keys_virtual_propagates_self_id` covering the `SqlaTable.get_extra_cache_keys` call site (patches `collect_rls_predicates_for_sql` and asserts `exclude_dataset_id=self.id`).
- M7: Add a test in `test_virtual_dataset_format.py` that asserts `_get_from_clause` invokes `apply_rls` with `exclude_dataset_id=<dataset.id>`.
- M10: Add an assertion that the lookup filter is an `and_` `BooleanClauseList` (`operator is operators.and_`).

### Coverage gap fixes
- `collect_rls_predicates_for_sql` (`rls.py:161-186`) — covered as a side effect of the new M5 propagation test, which exercises the happy path and indirectly increases line/branch coverage on the module.

### Behavioral gap fixes
- None additional: each surviving mutation maps cleanly to an existing PR-changed code path.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| tests/unit_tests/sql_lab_test.py | Extended `test_get_predicates_for_table_excludes_self` to assert wrapping operator (`operators.and_`), exclusion clause operator (`operators.ne`), left key (`id`), and right value (`42`). | M1, M2, M10 |
| tests/unit_tests/sql_lab_test.py | New `test_apply_rls_propagates_exclude_dataset_id` calling `apply_rls(..., exclude_dataset_id=42)` and asserting both `get_predicates_for_table` calls carry it. | M4 |
| tests/unit_tests/sql_lab_test.py | New `test_collect_rls_predicates_for_sql_propagates_exclude_dataset_id` covering the cache-key wrapper with `exclude_dataset_id=42`, plus indirect coverage of `collect_rls_predicates_for_sql` body. | M5, +14pp line coverage on `superset/utils/rls.py` |
| tests/unit_tests/models/test_double_rls_virtual_dataset.py | New `test_get_extra_cache_keys_passes_self_id_to_collect` mocking `SqlaTable` and asserting the cache-key call carries `exclude_dataset_id=self.id`. | M6 |
| tests/unit_tests/models/test_virtual_dataset_format.py | New `test_apply_rls_receives_self_id_as_exclude_dataset_id` setting `virtual_datasource.id = 4242` and asserting `apply_rls.call_args.kwargs["exclude_dataset_id"] == 4242`. | M7 |

## Final verification

Targeted suite: 33 passed, 0 failed
Line coverage: 93% (33/35)
Branch coverage: 88% (7/8)
Kill rate: 10/10 (100%) — full rerun

Remaining uncovered lines on `superset/utils/rls.py`: 183, 186 (defensive `except Exception` branch in `collect_rls_predicates_for_sql`).

## Final assessment

The targeted suite started at 79% line / 88% branch with a kill rate of 30%: only the guard mutation, the `getattr` fallback, and the guest-RLS flag flip were detected. The seven survivors all fell into two patterns of weak assertions:

- Clause-count-only assertions on the new exclusion filter (M1, M2, M10) that ignored which operator/operand was actually used and whether the wrapping clause was AND vs OR.
- Default-value propagation gaps (M4, M5, M6, M7) where every test path went through `exclude_dataset_id=None`, so removing propagation was invisible.

Five new assertions / tests were added across three files; the rerun ends at 93% line / 88% branch and 100% kill rate, exactly the contract this PR needs: the operator, the operand, the AND-vs-OR wrapping, and the propagation through every wrapper and both call sites are now asserted directly.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `collect_rls_predicates_for_sql` error path | A test that feeds in unparseable SQL and asserts the function returns `[]` (the `except Exception:` branch at `superset/utils/rls.py:183-186`). | This is the only un-hit code path in the module; without coverage, a regression that swallows the wrong exception type would be silent. |
| Multi-statement SQL | A test that runs `collect_rls_predicates_for_sql` against a SQLScript with two statements and asserts both tables are looked up. | The `SQLScript` parse path is touched but not asserted in detail — a regression that drops the inner loop would not affect any current test. |
| End-to-end physical→virtual conversion | A higher-level integration test that creates a real RLS rule for `orders`, queries via a virtual dataset whose inner SQL hits the same table, and asserts only one set of predicates is applied. | Existing tests assert mechanics; an integration test would directly assert the bug-class behavior at the API boundary. |

## Mutation quality self-assessment

- Initial kill rate: 30% — well under the 50–80% "well-targeted" band, which validates the choice of gap mutations: they exposed real assertion weakness, not artifacts of overly clever tests.
- Gap/strength ratio: 8/10 (80%) — matches the planned 75/25 mix with a slight gap bias; both strength mutations (M3, M9) killed by the existing suite confirmed the deliberately protected behaviors.
- Failure areas covered: 6/7 applicable (`error handling` was not applicable for this PR — the change adds a new optional parameter rather than new error surfaces).
- Mutations informed by coverage analysis: 10/10 — every mutation targets either an uncovered branch, an assertion-count blind spot, or an untested propagation step identified before execution.
