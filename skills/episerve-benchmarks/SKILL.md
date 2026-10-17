---
name: episerve-benchmarks
description: Use only when the request explicitly asks about EPISERVE benchmarks -- list or show benchmarks, read a leaderboard, get the run spec to run a model on a benchmark's pinned data, add a finished model run to a leaderboard, or design (create, check, finalize, copy, retire) a benchmark. Not triggered by default; for plain catalog queries use episerve-data-access and for starting a model run episerve-model-runs.
---

# EPISERVE benchmarks

A **benchmark** fixes one time series (a processed dataset QID, a target
column, a date column and an optional single equality filter), an **input
range** (what a model may see) and a **reference range** (`test_start` ..
`test_end`, what forecasts are scored against), and pins ONE lakeFS commit of
the data once it is final. A model run made from it is an **entry**: scored
once when added, then ranked on the benchmark's **leaderboard**.

This skill uses the latest `episerve` CLI release. If `episerve benchmark -h`
fails, the installed client is outdated -- say so and ask for an update rather	han working around it.
Connection variables and the daily-rotating `EPISERVE_API_KEY` are the same as
in `episerve-data-access`; read that skill for `list` and `item`, and
`episerve-model-runs` for starting a run.

Only act if the request explicitly asks. Reading is harmless; every write
below is only done when the request says so.

## Reads (no login needed)

```bash
episerve benchmark list                               # final benchmarks + entry counts
episerve benchmark show 3                             # definition and state
episerve benchmark leaderboard 3                      # best entry per model, ranked
episerve benchmark leaderboard 3 --rank-by mae --all-runs
episerve benchmark run-spec 3                         # what a run needs (final benchmarks only)
```

`--rank-by`: `interval_score` (default, lower is better), `mae`, `rmse`
(lower is better), `coverage` (share inside the 80% interval, closest to 0.8
is best). Output is JSON on stdout; the banner goes to stderr. A leaderboard
only reads stored scores -- it makes no call to the data stores.

`run-spec` returns `benchmark_id`, `dataset_qid`, `data_commit`,
`input_data_files` (`[[url-with-?version=<data_commit>, file-name]]`),
`data_transformation_sql`, `config` (e.g. `prediction_length`,
`prediction_offset`) and the test range. It has the shape of a model-run
request but lacks the model.

## Running a model on a benchmark

1. `episerve benchmark run-spec <id> > spec.json`
2. Add `model_image` (and `model_tag`) and the model's own `config` keys to
   `spec.json`, keeping the benchmark's `input_data_files` and
   `data_transformation_sql` **unchanged** -- the input must be read at the
   pinned commit or the run is refused later. `run-spec` fills only
   `prediction_length` and `prediction_offset`; the model's other required keys
   (commonly `history_length`: the number of input rows after the SQL) are yours
   to add -- see "The config" in `episerve-model-runs`.
3. `episerve trigger-model-run spec.json` (a real cluster job -- only when the
   request asks; see `episerve-model-runs`). Wait for the run to finish
   and note its run QID.
4. `episerve benchmark add-entry <id> <run-QID>` (needs a token).

A run can be added only if it succeeded, has the benchmark's dataset as
**exactly one** input read at `?version=<data_commit>`, its history ends
before `test_start` (read from the applied SQL: a single upper date bound,
written as `DATE 'YYYY-MM-DD'`, `'YYYY-MM-DD'` or `CAST(col AS DATE)`; SQL with
`OR`, `NOT`, `UNION`/`EXCEPT`/`INTERSECT` or `INTERVAL` is not scorable), the
benchmark's filter appears as an equality condition, and it forecasts every
observed date in the reference range. Coverage and interval score need the
`<target>_q10` and `<target>_q90` columns in `predictions.tsv`.

A just-finished run can take up to about an hour to appear in the catalog:
an `add-entry` for an unknown run QID fails with 404 -- wait and retry later,
not in a tight loop. If the run is refused (422), the reason is printed and
nothing is stored; report it verbatim. A run that is already on the board
returns 409.

## Writes (need a token)

All need `EPISERVE_API_KEY` (or `--api-key`); `401`/`403` means missing or
expired -- report it, don't retry in a loop.

```bash
episerve benchmark drafts                              # list drafts
episerve benchmark create benchmark.json               # or an inline JSON string
episerve benchmark update 3 '{"test_end": "2026-08-31"}'   # drafts only; null clears an optional field
episerve benchmark check 3                             # read-only: problems, warnings, forecast length, SQL
episerve benchmark finalize 3
episerve benchmark copy 3                              # new draft with the same definition
episerve benchmark retire 3
episerve benchmark remove-entry 3 <entry-id>           # soft delete; add-entry again recomputes
```

`create` JSON -- required: `name`, `dataset_qid`, `target_column`,
`date_column`, `test_start`, `test_end` (dates `YYYY-MM-DD`); optional:
`description`, `filter_column`, `filter_value` (one equality filter that
selects a single series), `history_start`, `history_end` (empty = the last
observation before `test_start`), `input_filename` (default `input.parquet`).
Take `dataset_qid` from `episerve list datasets`, never invent one.

Rules for the writes:
- Always run `check` on a draft before `finalize` and stop if it reports
  problems.
- **`finalize` is irreversible**: it pins whatever the lakeFS head is at that
  moment and makes the benchmark immutable. A final benchmark is changed only
  by `copy` (new draft). Only finalize when the request says to.
  Only the **creator** of a draft can finalize it (the account that created or copied it);
  anyone else gets `403` -- report that instead of trying another way.
- `retire` hides the benchmark from the lists and blocks new entries; its
  leaderboard stays readable. Only when asked.
- There is no delete: removal and retirement are soft.

## Verifying

Before your final message claims a benchmark call succeeded, confirm the JSON
you saw on stdout (a benchmark list, a leaderboard with entries, an
`entry_id`, a state change from a following `show`). Errors print
`HTTP <code>: <detail>` to stderr and exit non-zero -- quote them. Don't
state leaderboard ranks, scores or "best model" from memory or from a
different `--rank-by` than you ran.
