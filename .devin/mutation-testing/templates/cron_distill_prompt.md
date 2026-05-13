<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Cron distillation — agent handoff

You are running the periodic distillation pass over committed mutation-testing logs.
The Devin GitHub integration is already authenticated for this repository, so plain
`git` commands work without any extra setup. Do **not** run `gh auth login`,
`gh auth setup-git`, `gh pr checkout`, `git remote set-url`, or `export GH_TOKEN=...`.

## Inputs

* `.devin/mutation-testing/pr-*.md` — every committed per-PR log file, conforming
  to `template_02_mutation_testing.md`. Each file's YAML front matter contains
  `pr_id`, `run_date`, `initial_state`, `final_state` (kill rate, coverage, test
  counts), and the structured body contains the weak-spot analysis and
  "What's left for high-quality coverage" sections.
* `docs/test-quality/README.md` — the committed seed/snapshot of the dashboard
  (do **not** edit; the live dashboard lives in the GitHub Wiki).
* **All prior `Test-Quality-*.md` entries already on the wiki** — every previous
  distillation run is preserved on the wiki as a dated page (`Test-Quality-YYYY-MM-DD.md`).
  You **must read these** before writing the new entry so the new page can
  reference the trend (e.g. kill rate over the last N runs, patterns that
  recur across multiple distillations). They are append-only history; do not
  rewrite or delete them.

## Output target — GitHub Wiki, dated history, not a PR

This pass does **not** open a pull request. Engineering leaders don't need a PR
to read a status dashboard, and routing dashboards through code review pollutes
the PR queue. Instead, the canonical output is the **`Test Quality` page set on
the repository's GitHub Wiki**, organised as a dated history:

* **Per-run dated entry** — each distillation run creates a brand-new page named
  `Test-Quality-YYYY-MM-DD.md` (or `Test-Quality-YYYY-MM-DD-HHMM.md` if a page
  for today already exists from an earlier run). Use the current **UTC** date/time
  from your environment (e.g. `date -u +%Y-%m-%d` / `date -u +%Y-%m-%d-%H%M`).
  This page is the full distilled report for that run. Prior dated entries are
  **never edited or deleted** — they are append-only history.
* **Index page** — `Test-Quality.md` is the landing page of the dashboard. It
  contains a one-line summary of the latest run, a chronological history table
  of every prior dated entry, and the workflow description. Each run refreshes
  the index in place to point at the new entry and add a new history row.

GitHub Wiki is the natural home for project documentation: a VP of engineering
or PM expects to read it there, it's auto-indexed by the repository, and it
doesn't require any special tooling to view. The wiki is a sibling git
repository at `<repo>.wiki.git`; clone it inside the session, write the new
dated entry, refresh the index, and push. The Devin GitHub integration is
authenticated for the parent repo, which extends to the wiki.

## Notification channels

After the wiki is updated, share the highlights through the channels listed
in the `{{ NOTIFICATION_CHANNELS }}` placeholder (passed in from the workflow
input). Format is a comma-separated list, e.g.
`slack:#test-quality,linear:ENG,teams:eng-quality`. Supported channels:

| Channel | Format | Required secret/var |
|---|---|---|
| Slack | `slack:#channel-name` | `SLACK_WEBHOOK_URL` |
| Linear | `linear:TEAM_KEY` | `LINEAR_API_KEY` |
| Microsoft Teams | `teams:webhook-name` | `TEAMS_WEBHOOK_URL` |
| Email digest | `email:list@company.com` | `SMTP_*` standard vars |
| (none) | empty string | — — wiki entry only |

For each configured channel:
* **Title + headline summary + link only.** Title of the new dated entry,
  one-line summary of the headline numbers (PRs processed / PRs at 100% kill
  rate / total tests added), and a link to the full dated entry on the wiki.
  No tables, no charts, no full action plan in the chat surface.
* If a channel is listed but its required secret/var is missing, skip it
  silently in the run summary (do not fail the run; this is graceful
  degradation, not an error).
* Do not paste the distillation into chat surfaces. Chat is the pointer layer;
  the wiki is the destination.

## Content of the dated entry (`Test-Quality-YYYY-MM-DD.md`)

The dated entry **must** start with a YAML front matter block so future runs
can parse it programmatically without re-reading the markdown body. The front
matter is the contract; if you cannot source a number from a log, omit the key
(do not invent a value).

```yaml
---
run_date: "YYYY-MM-DD"
run_timestamp: "YYYY-MM-DDTHH:MM:SSZ"   # ISO-8601 UTC
distillation_window_days: 30
source_commit: "<short SHA of the repo HEAD at distillation time>"
prs_processed: <int>
prs_at_100_kill_rate: <int>
prs_needed_foundation: <int>
total_tests_added: <int>
prs_left_unsafe: <int>
previous_entry: "Test-Quality-YYYY-MM-DD"   # filename without .md, or null on first run
---
```

Then the body, in this order:

1. **Run metadata block** at the top (also visible to humans): distillation
   window, run timestamp, source commit SHA, link to the previous dated entry
   (if any).
2. **Headline numbers** for the distillation window (PRs processed · PRs
   reaching 100% kill rate · PRs that needed foundation · total tests added ·
   PRs left at unsafe kill rate).
3. **Change vs. previous run** — a 2–4 line paragraph or a small table contrasting
   this run's headline numbers with the previous dated entry's front matter.
   If this is the first run, write "First distillation — no prior run to compare against."
4. **Per-PR snapshot table** (PR link, title, foundation flag, initial kill,
   final kill, final line coverage, tests added). Order by `run_date` descending.
5. **Mutation kill-rate trend chart** — Mermaid `xychart-beta`, one bar pair
   per PR in this window (initial vs. final kill rate).
6. **Cross-run kill-rate trend** — Mermaid `xychart-beta` using each prior
   dated entry's `prs_at_100_kill_rate / prs_processed` ratio (one bar per run,
   chronological). Skip this section if there are fewer than two runs in
   history.
7. **Patterns we keep finding** — recurring shapes across PRs *and* across
   runs (e.g. clause-count assertions, default-value propagation gaps,
   foundation-needed cases). Each row: pattern name, example PR(s), one-sentence
   explanation of why mutations slip past. When a pattern recurs in multiple
   prior dated entries, note that explicitly. Distill, don't enumerate.
8. **Recommended next actions** — distilled from each PR's "What's left for
   high-quality coverage" section, **plus** any unresolved actions from the
   previous dated entry's recommendations that no subsequent PR has addressed.
   Each row: priority, area, action, source PR(s). The action plan is the
   load-bearing part of the page; spend more thought here than on the
   headline numbers.
9. **JA summary** — short bilingual mirror at the bottom (`<details>` block).

## Content of the index page (`Test-Quality.md`)

The index is short and stable; it does **not** repeat the full body of the latest
dated entry. Sections, in order:

1. Title and one-line description of what the dashboard is.
2. **Latest run** — a one-line summary (date + headline numbers) plus a link
   to the most recent dated entry.
3. **History** — a chronological table (newest first) with one row per dated
   entry. Columns: date, distillation window, PRs processed, PRs at 100% kill
   rate, total tests added, link to the entry.
4. **How this is refreshed** — short workflow description with a link to
   `devin-cron-distill.yml` and to `docs/test-quality/README.md` (the seed
   snapshot).

The index page is the only wiki file other than the new dated entry that you
are allowed to modify. Do **not** touch any prior `Test-Quality-YYYY-MM-DD.md`.

## How to do it

1. Inventory every `.devin/mutation-testing/pr-*.md` log file. Filter to those
   whose `run_date` falls inside the distillation window (default 30 days).
2. Parse the YAML front matter to extract metrics. Use the structured body
   sections (`Patterns`, weak-spot analysis, fix plan, "What's left for
   high-quality coverage") for qualitative distillation — do not re-summarise
   the entire log, only pull the items that recur or that remain unresolved.
3. Clone the wiki sibling repo (`git clone https://github.com/<owner>/<repo>.wiki.git`).
4. **Read prior history.** List every `Test-Quality-YYYY-MM-DD*.md` file on the
   wiki. Parse each one's YAML front matter to build a chronological record of
   `prs_processed`, `prs_at_100_kill_rate`, `total_tests_added`, and the
   filename. Read the most recent prior entry's `## Recommended next actions`
   section in full so the new entry can mark items that have since been
   addressed (a follow-up PR's log exists) versus still-open.
5. Determine the new dated entry filename. Default is `Test-Quality-$(date -u +%Y-%m-%d).md`.
   If that filename already exists on the wiki (rare same-day re-run), use
   `Test-Quality-$(date -u +%Y-%m-%d-%H%M).md`.
6. Write the new dated entry following the **Content of the dated entry**
   schema above, including the YAML front matter block.
7. Refresh the **index page** `Test-Quality.md` in place: update the "Latest
   run" pointer and prepend a new row to the history table.
8. Commit both files in one commit with the message
   `chore(test-quality): distill <new-entry-filename-without-extension>` and push.
   (For a wiki repo, push to the default branch via `git push origin HEAD` —
   the wiki is a single-branch repo, there is no PR workflow.)
9. For each notification channel in `{{ NOTIFICATION_CHANNELS }}`, post the
   title + headline summary + link to the new dated entry. Do not paste the
   page body into chat surfaces.
10. Write a single-line summary to the GitHub Actions run summary
    (`actions/core.summary`) with the new dated entry URL, the index page URL,
    and the number of channels notified.

## Constraints

* Do **not** rewrite or edit the per-PR log files. They are append-only history.
* Do **not** edit `docs/test-quality/README.md`. It is a committed seed/snapshot;
  the live dashboard lives in the GitHub Wiki.
* Do **not** edit or delete any prior `Test-Quality-YYYY-MM-DD*.md` dated entry
  on the wiki. They are append-only history, parallel to the per-PR logs.
* Do **not** invent metrics that aren't in the log file YAML. If a number can't
  be sourced from a log, omit it.
* The YAML front matter on the new dated entry is **required** — future runs
  parse it to build cross-run trend data. If you cannot source a key, omit it
  (do not write a placeholder).
* Keep the action plan to ≤ 8 items. Prioritise items that recur across multiple
  PRs *and* across multiple dated entries over one-offs. If fewer than 8 items
  exist, that's fine — fewer is better than padded.
* If two PRs share an action area (e.g. both call out an integration test on the
  same module), collapse into one row and cite both PRs as sources.
* If a previous dated entry's recommendation has been addressed by a subsequent
  PR (its log exists in `.devin/mutation-testing/pr-*.md`), do not re-list it;
  the closed loop is the point of this workflow.
* If the distillation window contains zero logs, still create the dated entry
  (with a "no activity in window" note), still refresh the index, and skip
  notifications.

## Why this exists

Coverage tells you which lines executed. Kill rate tells you which lines are
actually protected by assertions that would fail if the behaviour changed.
The dated GitHub Wiki history is the closed-loop knowledge layer: every PR
contributes a log, each distillation pass surfaces what's still weak and
preserves its own snapshot for later trend analysis, and team members kick off
the next round of uplift Devins against the recommended actions — whose
results feed back into the next distillation. Reading the prior dated entries
before writing a new one is what turns this from a recurring screenshot into a
durable trend record.
