---
name: episerve-model-runs
description: Use only when the request explicitly asks to start a forecast model run on the live EPISERVE platform, or to check on a model run's status or fetch its result. Starting a run consumes cluster resources and cannot be undone. Not triggered by default. For listing datasets/models and downloading files use episerve-data-access; for scoring a run against a benchmark use episerve-benchmarks.
---

# EPISERVE model runs

Start a forecast model on the platform and follow it to its result, through
the `episerve` CLI (same binary, connection variables and token as
`episerve-data-access`; read that skill for `list`, `item` and the variables).
Starting a run needs a personal `EPISERVE_API_KEY` (valid for one day) of a user with the right `runs`.
In the task runner it is already set. If a write answers `401`, the token is missing or expired; if `403`,
the user lacks the right `runs`. Report that instead of guessing.

Only act if the request explicitly asks to start a run (wording like "trigger
a model run for ...", "forecast X with the timesfm model") or to check or
fetch an existing one. If it doesn't, do nothing in this skill.

## Before you start

This skill needs the `episerve` CLI. Check it with `command -v episerve && episerve --cli-version` (exit 0 = up to
date, 1 = a newer release exists, 2 = check failed). If it is missing or outdated, say so and give the user the
install line from `episerve-data-access` ("Before you start"); do not install anything unless the request asks you to.

## Find the pieces first

```bash
episerve list models      # model_image / tag of the registered models
episerve list datasets    # dataset QIDs and their DOIP links
```

Take the model image and the input from these listings -- never invent a QID
or an image name. Each model lists its parameters in `additional_properties`
(`name`, `valueRequired`, `minValue`, `maxValue`, `value` = default); see
"The config" below. To run on a **benchmark's** pinned data, take the input and
SQL from `episerve benchmark run-spec <id>` instead (see
`episerve-benchmarks`) and keep them unchanged.

## Start a run -- the one write

Treat this like opening a PR: **only** if the request explicitly says to
trigger / start / launch a model run. It consumes real Kubernetes cluster
resources and cannot be undone or dry-run -- never fire one speculatively or
"to test that it works".

```bash
episerve trigger-model-run '{
  "model_image": "ghcr.io/the-episerve-consortium/model__prediction__generic__timesfm",
  "model_tag": "latest",
  "input_data_files": [["<lakefs:// URI or DOIP retrieve URL>", "input.parquet"]],
  "config": {"history_length": 512, "prediction_length": 182},
  "data_transformation_sql": ["SELECT ... FROM df WHERE ..."]
}'
```

(the argument is an inline JSON string or a path to a JSON file). `model_image`,
`input_data_files` (a list of `[source_uri, target_filename]` pairs), and `config`
(a JSON object -- the API serializes it to `config_json` for the flow) are
required; `model_tag` and `data_transformation_sql` are optional.

### The config

`config` must contain **every parameter the model marks `valueRequired: true`**
(the `value` shown for it is not a default -- it is typically `null`), within its
`minValue` / `maxValue`. Read them before building the request:

```bash
episerve --raw list models      # find the model, read its additional_properties
```

Typical generic forecast models require `history_length` (rows of context) and
`prediction_length`; others use different names (e.g. `horizon_weeks`), so don't
assume. `episerve benchmark run-spec` fills only `prediction_length` and
`prediction_offset` -- add the model's other required keys yourself (for
`history_length` the number of rows in the input after the transformation SQL).

The API server rejects a config that misses a required key or breaks a bound with
`422` and lists every violation (`Invalid model config: ...`); fix the config
and send it again. Servers without that check accept the run and the model
container fails it a few seconds later with `config.json missing required key:
'<name>'` -- the same fix applies.

It returns `202` with a `run_id` (the Prefect flow-run UUID). Confirm a real
`run_id` came back (not an error) before claiming success, and state it
plainly. `401`/`403` means the token is missing or expired -- report it, don't
retry in a loop.

## Follow it

The run appears in the catalog under its run **QID** only after it finishes,
which can take up to about an hour after completion. Until then it is not
findable by QID; `trigger-model-run`'s `run_id` is a different identifier.

```bash
episerve list runs          # all runs with status, timestamps, input/output files
episerve run show Q<qid>    # status, timestamps, computation time, in/outputs of one run
```

Don't poll in a tight loop; if the run isn't listed yet, say so and check
again later. A run is registered when it ends, **whatever its outcome**: a
failed run appears in `list runs` with status `failed` (and only `success` runs
can be added to a benchmark). If a run's status is not `success`, report the
status as shown -- don't guess a cause; the reason is in the run's
`output/run.log`, which you can download with `item download`.

## Fetch the result

```bash
episerve item list-components Q<qid>
episerve item download Q<qid> output/predictions.tsv -o ./predictions.tsv
```

(component ids and download behaviour as in `episerve-data-access`). `ls -la`
the file to confirm it arrived with non-zero size before reporting it.

## Verifying

Before your final message claims a run was started: you saw a real `run_id`
on stdout. Before it claims a run finished or a result exists: you saw the
`success` status from `list runs` / `run show` and the file on disk. Errors
print `HTTP <code>: <body>` or `Connection error: ...` to stderr and exit
non-zero -- quote them, don't fabricate a result.
