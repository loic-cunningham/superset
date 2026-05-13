# Example: Test Foundation Plan — PR #7 Add rate limiting to MCP endpoints

## Test foundation plan — feat(mcp): Add rate limiting to MCP execute_sql and search endpoints

### Triage result

| Metric | Value |
|---|---|
| PR | #7 |
| Changed files | 4 |
| Existing test coverage (changed files) | 12% |
| Existing tests for changed behavior | 0 |
| Decision | **Create foundation tests** |
| Reason | No tests exist for rate limiting behavior. The only coverage is indirect from unrelated MCP tests that happen to import the changed modules. |

### Critical guarantees to cover

| # | Critical guarantee | Priority | Target test location |
|---|---|---|---|
| 1 | Requests within limit succeed | High | `tests/unit_tests/mcp_service/test_rate_limiter.py` |
| 2 | Requests exceeding limit are rejected with 429 | High | `tests/unit_tests/mcp_service/test_rate_limiter.py` |
| 3 | Rate limit resets after window expires | High | `tests/unit_tests/mcp_service/test_rate_limiter.py` |
| 4 | Rate limit is per-user, not global | Medium | `tests/unit_tests/mcp_service/test_rate_limiter.py` |
| 5 | Rate limit decorator applies to execute_sql | High | `tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py` |
| 6 | Rate limit decorator applies to search | Medium | `tests/unit_tests/mcp_service/search/test_search.py` |

### Test plan per changed file

#### `superset/mcp_service/rate_limiter.py`

**Changed behavior:**
- New `RateLimiter` class with sliding window algorithm
- `@rate_limit(max_calls, window_seconds)` decorator

**Tests to create:**

| Test name | What it verifies | Inputs | Expected outcome |
|---|---|---|---|
| `test_rate_limiter_allows_within_limit` | Requests within the configured limit succeed | 5 calls, limit=10 | All 5 return normally |
| `test_rate_limiter_rejects_over_limit` | Requests exceeding the limit are rejected | 11 calls, limit=10 | 11th raises `RateLimitExceeded` |
| `test_rate_limiter_resets_after_window` | Rate limit resets after the time window | 10 calls, wait, 1 more call | 11th call succeeds after window expires |
| `test_rate_limiter_per_user_isolation` | Different users have independent limits | 10 calls user A, 1 call user B | User B succeeds despite user A at limit |
| `test_rate_limiter_concurrent_requests` | Thread safety of the counter | 20 concurrent calls, limit=10 | Exactly 10 succeed, 10 rejected |

**Edge cases:**
- Zero limit configuration
- Negative window seconds
- Missing user context (should fail closed)

**Mocking requirements:**
- `time.monotonic()` for window expiration tests
- `threading.Lock` for concurrency tests

#### `superset/mcp_service/sql_lab/tool/execute_sql.py`

**Changed behavior:**
- `@rate_limit(max_calls=100, window_seconds=60)` applied to `execute_sql`

**Tests to create:**

| Test name | What it verifies | Inputs | Expected outcome |
|---|---|---|---|
| `test_execute_sql_rate_limited` | Rate limit decorator is active on execute_sql | 101 calls in <60s | 101st returns 429 error |
| `test_execute_sql_normal_under_limit` | Normal execution unaffected by rate limiter | 1 valid SQL call | SQL executes and returns result |

**Edge cases:**
- Rate limit hit during an active query (should not interrupt running query)

**Mocking requirements:**
- `database.execute()` for SQL execution
- `RateLimiter` instance for limit simulation

### Sub-agent assignments

| Sub-agent | Module/files | Test file(s) to create | Target coverage |
|---|---|---|---|
| 1 | `rate_limiter.py` | `test_rate_limiter.py` | 90% of rate_limiter.py |
| 2 | `execute_sql.py`, `search.py` | `test_execute_sql.py`, `test_search.py` | Rate limit paths in both files |

### Verification checklist

After foundation tests are written:

- [x] All new tests pass: `pytest tests/unit_tests/mcp_service/test_rate_limiter.py tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py -q` → 12 passed
- [x] Coverage of changed files is at least 50% → 78% line coverage on `rate_limiter.py`, 55% on `execute_sql.py`
- [x] Each critical guarantee has at least one assertion
- [x] Tests follow project conventions (pytest fixtures, MagicMock, no Enzyme)
- [x] Foundation tests committed: `git commit -m "test: add foundation tests for MCP rate limiting"`
