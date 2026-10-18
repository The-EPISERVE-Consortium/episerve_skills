---
name: episerve-data-access
description: Use only when the request explicitly asks to look something up on the live EPISERVE platform -- check platform health, list datasets / models / model runs, read an item's catalog record by QID, list an FDO's components, or download a component (latest version). Read-only. Not triggered by default and not implied by EPISERVE_* env vars being present. Starting a model run is episerve-model-runs; benchmarks are episerve-benchmarks.
---

# EPISERVE data access

Query a running EPISERVE deployment through the `episerve` CLI (a static
binary from the `episerve_client` GitHub release), which fronts three
backends: the **API server** (health, catalog listings), the **CKAN catalog** (an item's registered metadata record), and the
**DOIP server's HTTP gateway** (listing and downloading an FDO's components,
latest version only).

Only act if the request explicitly asks for one of these things (wording like
"list the available datasets", "show the record of Q...", "download the
predictions for run Q..."). The mere presence of `EPISERVE_API_URL` etc.
in the environment is not that instruction. If the request doesn't ask, do
nothing in this skill.

## Which skill

This skill is **read-only**. Use it to find and fetch; the other skills act:

| You want to... | Skill |
|---|---|
| Check platform health; list datasets / models / model-runs | **this skill** |
| Get an item's **CKAN catalog record** | **this skill** |
| List an FDO's components / download a component **at its latest version** | **this skill** -- HTTP, streamed, handles large files |
| **Start a model run** and follow it to its result | **`episerve-model-runs`** |
| List benchmarks, read a leaderboard, add a run to a leaderboard, design a benchmark | **`episerve-benchmarks`** |
| Download a component **at a specific commit**; list an object's **version history**; **write/replace** a component; **invoke** a server-side workflow; `hello`/`list_ops`; purge the manifest cache | **`doip-fdo-access`** -- those exist only over the native DOIP protocol |

If a task needs both (e.g. "list the runs, then fetch run Q...'s output at
commit abc123"), use this skill for the catalog part and `doip-fdo-access`
for the version-pinned fetch.

## Before you start

Check that the CLI is installed and current:

```bash
command -v episerve && episerve --cli-version   # exit 0 = up to date, 1 = a newer release exists, 2 = check failed
```

If `episerve` is not found, or the check reports a newer release, say so in your answer and give the user the
install line below. Do not download or install anything unless the request asks you to.

```bash
# Linux (use episerve-client-macos on a Mac); ~/.local/bin must be on PATH
curl -fsSL -o ~/.local/bin/episerve https://github.com/The-EPISERVE-Consortium/episerve_client/releases/latest/download/episerve-client-linux && chmod +x ~/.local/bin/episerve
```

Windows: download `episerve-client-windows.exe` from https://github.com/The-EPISERVE-Consortium/episerve_client/releases/latest, rename it to `episerve.exe` and put it in a folder
on the `PATH`. Then confirm that the variables in the Connection table below are set (`printenv <name>`) and name the missing ones.

## Connection

Expected in the environment -- don't ask for credentials, don't guess a host.
The `episerve` binary reads all of these itself:

| Env var | Meaning |
|---|---|
| `EPISERVE_API_URL` | API-server base URL (`health`, `list`) |
| `EPISERVE_CKAN_URL` | CKAN base URL (`item show`) |
| `EPISERVE_DOIP_URL` | DOIP **HTTP gateway** base URL (`item list-components`, `item download`) |
| `EPISERVE_API_KEY` | Bearer token for the API server. **Daily-rotating** (the api-server issues a token that expires each day). Not needed for the reads in this skill; `episerve-model-runs` and the write commands of `episerve-benchmarks` need it. |

For the public EPISERVE platform the values are:

```bash
export EPISERVE_API_URL=https://api.episerve.zib.de
export EPISERVE_CKAN_URL=https://data.episerve.zib.de
export EPISERVE_DOIP_URL=https://doip.episerve.zib.de
```

`episerve` has no built-in default: without these it tries a placeholder host and fails with a connection error.
The reads in this skill need no login.

If an env var needed for what the request asked is unset or empty, that's a
real failure -- say so explicitly in your final summary rather than silently
skipping the call. An `HTTP 401`/`403` on stderr means the token is missing
or expired -- report it verbatim, don't retry in a loop.

## How to call it

`episerve <command>` prints the result as **JSON on stdout**; a banner and a
`  -> <url>` progress line go to **stderr** (ignore them -- parse stdout
only). Add `--raw` for compact single-line JSON.

```bash
episerve health
episerve list runs                 # or: datasets | models
episerve item show Q1748526042817  # CKAN catalog record
episerve item list-components Q1748526042817
episerve item download Q1748526042817 output/predictions.tsv \
  -o ./predictions.tsv
```

A QID is `Q` followed by digits (13 in practice). Treat it as an opaque string -- never invent one; take it from
prior `list` / `item list-components` output or from the request.

The component id for `item download` is exactly what `item
list-components` returns as `id` -- the FDO `@id` with the leading
`components/` stripped. A model run's ids look like `output/predictions.tsv` or `input/config.json`; a dataset's
is usually just a file name (e.g. `COVID-19-Faelle_7-Tage-Inzidenz_Bundeslaender.parquet`).
Passing the un-stripped `components/...` form gets a 404. Always copy the id
from the listing rather than constructing it.

## Reads

`health`, `list`, `item show`, `item list-components`, `item download` are
safe whenever the request asks. `item download` writes the file at the `-o`
path (omit `-o` and it streams to stdout -- always use `-o`, pointing at the
output directory the task specifies, or the current directory). After a
download, `ls -la` the file to confirm it arrived with non-zero size. Never
report a file as downloaded without checking.

## Verifying

Before your final message claims a platform call succeeded: confirm you saw
the actual result on stdout (a non-empty JSON list, a record, a file on
disk). The `episerve` binary prints `HTTP <code>: <body>` or `Connection
error: ...` to stderr and exits non-zero on failure -- quote that in your
summary, don't fabricate a result and don't silently skip the step.
