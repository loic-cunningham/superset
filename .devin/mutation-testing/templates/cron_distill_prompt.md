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
  (do **not** edit; the live dashboard lives in Devin Wiki).

## Output target — GitHub Wiki, not a PR

This pass does **not** open a pull request. Engineering leaders don't need a PR
to read a status dashboard, and routing dashboards through code review pollutes
the PR queue. Instead, the canonical output is the **`Test Quality` page on the
repository's GitHub Wiki**, refreshed in place each run.

GitHub Wiki is the natural home for project documentation: a VP of engineering
or PM expects to read it there, it's auto-indexed by the repository, and it
doesn't require any special tooling to view. The wiki is a sibling git
repository at `<repo>.wiki.git`; clone it inside the session, edit
`Test-Quality.md`, and push. The Devin GitHub integration is authenticated
for the parent repo, which extends to the wiki.

## Notification channels

After the wiki entry is updated, share the highlights through the channels
listed in the `{{ NOTIFICATION_CHANNELS }}` placeholder (passed in from the
workflow input). Format is a comma-separated list, e.g.
`slack:#test-quality,linear:ENG,teams:eng-quality`. Supported channels:

| Channel | Format | Required secret/var |
|---|---|---|
| Slack | `slack:#channel-name` | `SLACK_WEBHOOK_URL` |
| Linear | `linear:TEAM_KEY` | `LINEAR_API_KEY` |
| Microsoft Teams | `teams:webhook-name` | `TEAMS_WEBHOOK_URL` |
| Email digest | `email:list@company.com` | `SMTP_*` standard vars |
| (none) | empty string | — — wiki entry only |

For each configured channel:
* **Title + headline summary + link only.** Title of the wiki page,
  one-line summary of the headline numbers (PRs processed / PRs at 100%
  kill rate / total tests added), and a link to the full wiki page.
  No tables, no charts, no full action plan in the chat surface.
* If a channel is listed but its required secret/var is missing, skip it
  silently in the run summary (do not fail the run; this is graceful
  degradation, not an error).
* Do not paste the distillation into chat surfaces. Chat is the
  pointer layer; the wiki is the destination.

## Content of the wiki page

1. **Headline numbers** for the distillation window
   (PRs processed · PRs reaching 100% kill rate · PRs that needed foundation ·
   total tests added · PRs left at unsafe kill rate).
2. **Per-PR snapshot table** (PR link, title, foundation flag, initial kill,
   final kill, final line coverage, tests added). Order by `run_date` descending.
3. **Mutation kill-rate trend chart** — Mermaid `xychart-beta`, one bar pair
   per PR (initial vs. final kill rate).
4. **Patterns we keep finding** — recurring shapes across PRs (e.g. clause-count
   assertions, default-value propagation gaps, foundation-needed cases).
   Each row: pattern name, example PR, one-sentence explanation of why mutations
   slip past. Distill, don't enumerate — the value is naming the pattern.
5. **Recommended next actions** — distilled from each PR's
   "What's left for high-quality coverage" section. Each row: priority,
   area, action, source PR. These are candidates a team member can kick off
   a Devin session against. The action plan is the load-bearing part of the
   page; spend more thought here than on the headline numbers.
6. **JA summary** — short bilingual mirror at the bottom (`<details>` block).
7. **Run metadata** at the top: distillation window, run date, source commit SHA.

## How to do it

1. Inventory every `.devin/mutation-testing/pr-*.md` log file. Filter to those
   whose `run_date` falls inside the distillation window (default 30 days).
2. Parse the YAML front matter to extract metrics. Use the structured body
   sections (`Patterns`, weak-spot analysis, fix plan, "What's left for
   high-quality coverage") for qualitative distillation — do not re-summarise
   the entire log, only pull the items that recur or that remain unresolved.
3. Clone the wiki sibling repo (`git clone https://github.com/<owner>/<repo>.wiki.git`).
   Edit `Test-Quality.md` — refresh in place if it exists; create it if not.
   Commit with a message like `chore(test-quality): distill <YYYY-MM-DD>` and push.
4. For each notification channel in `{{ NOTIFICATION_CHANNELS }}`, post the
   title + headline summary + link to the wiki page. Do not paste the
   page body into chat surfaces.
5. Write a single-line summary to the GitHub Actions run summary
   (`actions/core.summary`) with the wiki page URL and the number of channels
   notified.

## Constraints

* Do **not** rewrite or edit the per-PR log files. They are append-only history.
* Do **not** edit `docs/test-quality/README.md`. It is a committed seed/snapshot;
  the live dashboard lives in Devin Wiki.
* Do **not** invent metrics that aren't in the log file YAML. If a number can't
  be sourced from a log, omit it.
* Keep the action plan to ≤ 8 items. Prioritise items that recur across multiple
  PRs over one-offs. If fewer than 8 items exist, that's fine — fewer is better
  than padded.
* If two PRs share an action area (e.g. both call out an integration test on the
  same module), collapse into one row and cite both PRs as sources.
* If the distillation window contains zero logs, write a brief "no activity in
  window" note to the wiki page and skip notifications.

## Why this exists

Coverage tells you which lines executed. Kill rate tells you which lines are
actually protected by assertions that would fail if the behaviour changed.
The GitHub Wiki page is the closed-loop knowledge layer: every PR contributes a log,
distillation surfaces what's still weak, and team members kick off the next
round of uplift Devins against the recommended actions — whose results feed
back into the next distillation.
