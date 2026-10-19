---
name: episerve-model-runs-rest-fallback
description: Use only when the request explicitly asks to start a forecast model run on the live EPISERVE platform, or to check on / fetch a model run, AND the `episerve` CLI is not installed or the user does not want to install it. Same as episerve-model-runs, done with curl against the REST API. Starting a run consumes cluster resources and cannot be undone. Not triggered by default.
---

# EPISERVE model runs -- REST fallback

The same job as `episerve-model-runs`, with `curl` instead of the `episerve`
binary. Use it **only** if `command -v episerve` finds nothing (or the user
declined to install it); otherwise use `episerve-model-runs`. Only act if the
request explicitly asks to start a run, or to check or fetch an existing one.

```bash
API=${EPISERVE_API_URL:-https://api.episerve.zib.de}
DOIP=${EPISERVE_DOIP_URL:-https://doip.episerve.zib.de}
```

Reads (listings, status, results) are in `episerve-data-access-rest-fallback`
(`$API/models`, `$API/datasets`, `$API/model-runs`, `$DOIP/doip/retrieve/...`).

## Login (needed to start a run)

Starting a run needs a personal token, valid one day, of a user with the right
`runs`. Get it from the account's email and password (`EPISERVE_USERNAME` /
`EPISERVE_PASSWORD`); if they are not set, say so -- don't guess or ask for them
in the clear in a command.

```bash
TOKEN=$(jq -n --arg u "$EPISERVE_USERNAME" --arg p "$EPISERVE_PASSWORD" '{username:$u,password:$p}' \
  | curl -fsS -X POST $API/auth/token -H 'Content-Type: application/json' -d @- | jq -r .token)
curl -fsS $API/auth/status -H "Authorization: Bearer $TOKEN"   # shows expiry
```

Keep the token in a shell variable (or in `EPISERVE_API_KEY` if it is already
set); don't print it, don't write it to a tracked file. `401` = missing or
expired, `403` = the user lacks the right `runs`: report it, don't retry in a loop.

## Find the pieces first

`curl -fsS $API/models` (image / tag and `additional_properties`) and
`curl -fsS $API/datasets`. Never invent a QID or an image name. For a
benchmark's pinned data, take input and SQL from the run spec
(`episerve-benchmarks-rest-fallback`) and keep them unchanged.

## Start a run -- the one write

Only if the request explicitly says to trigger / start / launch a run. It
consumes real cluster resources, cannot be undone or dry-run; never fire one
"to test that it works".

```bash
curl -fsS -X POST $API/model-runs \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "model_image": "ghcr.io/the-episerve-consortium/model__prediction__generic__timesfm",
    "model_tag": "latest",
    "input_data_files": [["<lakefs:// URI or DOIP retrieve URL>", "input.parquet"]],
    "config": {"history_length": 512, "prediction_length": 182},
    "data_transformation_sql": ["SELECT ... FROM df WHERE ..."]
  }'
```

Required: `model_image`, `input_data_files` (list of `[source_uri, target_filename]`
pairs), `config` (a JSON object); optional: `model_tag` (default `latest`),
`data_transformation_sql`. `config` must contain every parameter the model marks
`valueRequired: true` in `additional_properties`, within `minValue` / `maxValue`
(`value` is not a default, usually `null`). A bad config answers `422`
with every violation (`Invalid model config: ...`); fix it and send again.
Use `curl -sS -w '\n%{http_code}\n'` instead of `-f` if you need to see the 422 body.

It returns `202` with a `run_id` (the Prefect flow-run UUID). Confirm a real
`run_id` came back before claiming success and state it plainly.

## Follow it and fetch the result

The run appears in the catalog under its run **QID** only after it finishes,
about a minute later; `run_id` is a different identifier. Don't poll in a tight loop.

```bash
curl -fsS $API/model-runs | jq '.[] | select(.status != "success") | {qid, status}'
curl -fsS $API/model-runs/Q<qid>                               # status, timestamps, in/outputs
curl -fsS -o ./predictions.tsv $DOIP/doip/retrieve/Q<qid>/output/predictions.tsv && ls -la ./predictions.tsv
```

A run is registered when it ends, whatever its outcome: a failed run shows up
with status `failed`. If the status is not `success`, report it as shown; the
reason is in `output/run.log` (same download URL pattern). Only `success` runs
can be added to a benchmark.

## Verifying

Claim a run started only after you saw a real `run_id`; claim it finished or a
result exists only after you saw status `success` and the file on disk. On
failure quote the HTTP status and body.
