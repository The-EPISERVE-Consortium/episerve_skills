---
name: episerve-data-access-rest-fallback
description: Use only when the request explicitly asks to look something up on the live EPISERVE platform (health, list datasets / models / model runs, a CKAN record by QID, an FDO's components, download a component) AND the `episerve` CLI is not installed or the user does not want to install it. Same reads as episerve-data-access, done with curl against the REST endpoints. Read-only. Not triggered by default.
---

# EPISERVE data access -- REST fallback

The same reads as `episerve-data-access`, with `curl` instead of the `episerve`
binary. Use this **only** if `command -v episerve` finds nothing (or the user
declined to install it). If the CLI is there, use `episerve-data-access`.
Only act if the request explicitly asks for a lookup; the presence of
`EPISERVE_*` variables is not that instruction.

Three servers, as in the CLI skill. For the public platform:

```bash
API=${EPISERVE_API_URL:-https://api.episerve.zib.de}     # health, listings, runs
CKAN=${EPISERVE_CKAN_URL:-https://data.episerve.zib.de}  # catalog record
DOIP=${EPISERVE_DOIP_URL:-https://doip.episerve.zib.de}  # components (HTTP gateway)
```

For another deployment ask its administrator; don't guess a host. None of the
calls below needs a login. Interactive API docs: `$API/docs`, schema `$API/openapi.json`
(the DOIP gateway has the same at `$DOIP/docs`).

## Command -> curl

| CLI | curl |
|---|---|
| `episerve health` | `curl -fsS $API/health` |
| `episerve list datasets` | `curl -fsS $API/datasets` |
| `episerve list models` | `curl -fsS $API/models` |
| `episerve list runs` | `curl -fsS $API/model-runs` |
| `episerve run show Q…` | `curl -fsS $API/model-runs/Q…` |
| `episerve item show Q…` | `curl -fsS "$CKAN/api/3/action/package_show?id=<qid lower-case>"` -> `.result` |
| `episerve item list-components Q…` | `curl -fsS $DOIP/doip/retrieve/Q…` -> `.kernel["fdo:hasComponent"]` |
| `episerve item download Q… <id> -o f` | `curl -fsS -o f $DOIP/doip/retrieve/Q…/<id>` |

```bash
curl -fsS $API/model-runs | jq '.[] | {qid, status, model_name}'

# CKAN wraps the record: check .success, read .result. The QID must be lower-case.
curl -fsS "$CKAN/api/3/action/package_show?id=q1748526042817" | jq '.success, .result'

# component ids = @id with the leading "components/" removed (what the CLI prints as `id`)
curl -fsS $DOIP/doip/retrieve/Q1748526042817 \
  | jq -r '.kernel["fdo:hasComponent"][] | [(.["@id"] | sub("^components/"; "")), .mediaType] | @tsv'

curl -fsS -o ./predictions.tsv $DOIP/doip/retrieve/Q1748526042817/output/predictions.tsv
ls -la ./predictions.tsv
```

Rules carried over from the CLI skill:
- A QID is `Q` + digits, an opaque string. Take it from a listing or from the
  request; never invent one.
- Copy the component id from the listing, without the `components/` prefix
  (the prefixed form gives 404). The component path may contain `/`; don't
  URL-encode it.
- Use `-fsS` so HTTP errors give a non-zero exit and a message. Always write
  downloads with `-o` and `ls -la` the file: never report a download without
  checking it arrived with non-zero size.
- Large files: curl streams them to disk; the gateway supports `Range` requests.
- A just-finished run appears in the catalog after about a minute.
- Restricted datasets (`access = restricted`): the component download answers
  401/403 without a signed link. Report that; don't look for a way around it.

## Reading only part of a large file

For a Parquet (or CSV/TSV) component you often need only some columns or rows. The DOIP HTTP gateway supports
HTTP range requests, so DuckDB can query the file in place and fetch only the bytes it needs, instead of
downloading it whole with `curl -o`:

```python
# pip install duckdb
import os, duckdb
url = f"{os.environ.get('EPISERVE_DOIP_URL', 'https://doip.episerve.zib.de')}/doip/retrieve/Q6940002821235/forecast.parquet"
print(duckdb.sql(f"""SELECT time, "temperature_2m_mean (°C)" FROM read_parquet('{url}')
                     WHERE time >= '2025-10-19'""").df())
```

- The URL is `$EPISERVE_DOIP_URL/doip/retrieve/<QID>/<component id>`, with the component id exactly as listed by
  the component listing above. Use `read_csv(...)` for `.tsv` / `.csv`.
- Look at the columns first with `DESCRIBE SELECT * FROM read_parquet('<url>')`. Name the columns you need
  instead of `*` and add a `WHERE` / `LIMIT`: the less you select, the less is read. How much is saved depends
  on how the file is stored; a small file is mostly read whole anyway.
- This needs the `duckdb` Python package. If it is not installed, say so and ask before installing it; otherwise
  fall back to `curl -o` and filter the local file.
- Restricted datasets answer 401/403 without a signed link; report that.
- Check what you got (row count, first and last date) before you report a result from the subset.

## Verifying

Before claiming a call succeeded, confirm you saw the actual result: a
non-empty JSON list, a record with `success: true`, a file on disk. On failure
quote the `curl` error or the HTTP status and body; don't fabricate a result.
