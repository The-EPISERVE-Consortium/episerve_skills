---
name: episerve-benchmarks-rest-fallback
description: Use only when the request explicitly asks about EPISERVE benchmarks (list or show, read a leaderboard, get the run spec, add a run to a leaderboard, design / check / finalize / copy / retire a benchmark) AND the `episerve` CLI is not installed or the user does not want to install it. Same as episerve-benchmarks, done with curl against the REST API. Not triggered by default.
---

# EPISERVE benchmarks -- REST fallback

The same job as `episerve-benchmarks` (read that skill for what a benchmark,
entry and leaderboard are, and for the rules), with `curl` instead of the
`episerve` binary. Use it **only** if `command -v episerve` finds nothing (or
the user declined to install it). Only act if the request explicitly asks;
every write below only when the request says so.

```bash
API=${EPISERVE_API_URL:-https://api.episerve.zib.de}
```

Schema and try-it-out: `$API/docs`, `$API/openapi.json`.

## Reads (no login)

| CLI | curl |
|---|---|
| `benchmark list` | `curl -fsS $API/benchmarks` |
| `benchmark show 3` | `curl -fsS $API/benchmarks/3` (a draft needs a token) |
| `benchmark leaderboard 3` | `curl -fsS "$API/benchmarks/3/leaderboard?rank_by=interval_score&all_runs=false"` |
| `benchmark run-spec 3` | `curl -fsS $API/benchmarks/3/run-spec` (final benchmarks only) |

`rank_by`: `interval_score` (default, lower is better), `mae`, `rmse`, `coverage`
(closest to 0.8 is best). Don't state ranks or scores from memory or from a
different `rank_by` than you ran. Download the generated files with the DOIP
URLs in `generated_files` of the `show` output (`input.url`, `reference.url`).

## Running a model on a benchmark

Same four steps as in `episerve-benchmarks`:

1. `curl -fsS $API/benchmarks/<id>/run-spec > spec.json`
2. Add `model_image` (and `model_tag`) and the model's own `config` keys with
   `jq`, keeping `input_data_files` **unchanged** (read in that version, nothing
   else, or the run is refused later). `run-spec` fills only `prediction_length`
   and `prediction_offset`; add the model's other required keys (commonly
   `history_length`). A `data_transformation_sql` on that file is allowed.
3. `POST $API/model-runs` with `spec.json` (see `episerve-model-runs-rest-fallback`;
   a real cluster job, only when the request asks). Wait for it to finish, note the run QID.
4. Add it to the board (below).

## Writes (need a token)

A personal token valid one day; get it as in `episerve-model-runs-rest-fallback`
("Login"; email and password from `EPISERVE_USERNAME` / `EPISERVE_PASSWORD`, never guessed).
Send `-H "Authorization: Bearer $TOKEN"`; `401`/`403` = missing / expired /
no right `benchmarks`: report it, don't retry in a loop. Add `-H 'Content-Type: application/json'` for bodies.

| CLI | curl |
|---|---|
| `benchmark drafts` | `GET $API/benchmarks/drafts` |
| `benchmark create f.json` | `POST $API/benchmarks -d @f.json` |
| `benchmark update 3 '{...}'` | `PATCH $API/benchmarks/3 -d '{...}'` (drafts only; `null` clears an optional field) |
| `benchmark check 3` | `POST $API/benchmarks/3/check` (read-only report) |
| `benchmark finalize 3` | `POST $API/benchmarks/3/finalize` |
| `benchmark copy 3` | `POST $API/benchmarks/3/copy` |
| `benchmark retire 3` | `POST $API/benchmarks/3/retire` (204, no body) |
| `benchmark add-entry 3 Q…` | `POST $API/benchmarks/3/entries -d '{"run_qid":"Q…"}'` |
| `benchmark remove-entry 3 <entry-id>` | `DELETE $API/benchmarks/3/entries/<entry-id>` (soft, 204) |

```bash
curl -fsS -X POST $API/benchmarks/3/check -H "Authorization: Bearer $TOKEN" | jq
curl -sS -w '\n%{http_code}\n' -X POST $API/benchmarks/3/entries \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"run_qid":"Q1748526042817"}'
```

Body fields of `create` (required: `name`, `dataset_qid`, `target_column`, `date_column`,
`test_start`, `test_end`; optional: `description`, `filters`, `history_start`,
`history_end`, `input_filename`, `covariates`) are described in `episerve-benchmarks`;
the exact schema is `components.schemas.BenchmarkCreate` in `$API/openapi.json`. Take
`dataset_qid` from `$API/datasets`, never invent one.

Rules (same as the CLI skill):
- Always `check` a draft before `finalize`; stop if it reports problems.
- **`finalize` is irreversible**: it pins the lakeFS head and makes the benchmark
  immutable. Only when the request says so. Only the draft's creator can do it
  (`403` otherwise; report it).
- `retire` hides the benchmark and blocks new entries; only when asked.
- No delete: removal and retirement are soft.
- Adding an entry: the run must have succeeded, read exactly the generated input
  file in the stored version, and forecast every observed date in the reference
  range. `404` for an unknown run QID: wait a minute (catalog delay) and retry,
  not in a tight loop. `422` = refused, quote the reason; `409` = already on the board.
- For writes use `-sS -w '\n%{http_code}\n'` rather than `-f`, so the error body is visible.

## Verifying

Claim success only after you saw the JSON (a list, a leaderboard with entries,
an `entry_id`, a state change from a following `GET`) or the expected status
(`204`). On failure quote the HTTP status and detail.
