---
name: doip-fdo-access-rest-fallback
description: Use only when the request explicitly asks for a version-aware DOIP operation on an FDO -- list an object's version history, retrieve a component at a specific commit, purge the manifest cache -- AND `episerve-doip-cli` is not installed or the user does not want to install it. Done with curl against the DOIP HTTP gateway. Cannot write (update), invoke workflows, or run hello/list_ops. Not triggered by default.
---

# DOIP FDO access -- HTTP gateway fallback

The version-aware reads of `doip-fdo-access`, with `curl` against the DOIP
**HTTP gateway** instead of the native-protocol `episerve-doip-cli`. Use it
**only** if `command -v episerve-doip-cli` finds nothing (or the user declined
to install it). Only act if the request explicitly asks for one of these.

```bash
DOIP=${EPISERVE_DOIP_URL:-https://doip.episerve.zib.de}   # not DOIP_HOST/DOIP_PORT: that is the binary protocol
```

Schema: `$DOIP/openapi.json`, docs `$DOIP/docs`. Latest-version listing and
download are in `episerve-data-access-rest-fallback`.

## What the gateway can and cannot do

| `doip-fdo-access` | HTTP gateway |
|---|---|
| `retrieve` (metadata) | yes: `GET $DOIP/doip/retrieve/<QID>` |
| `versions` | yes: `GET $DOIP/doip/versions/<QID>` |
| component `retrieve --version` | yes: `GET $DOIP/doip/retrieve/<QID>/<component>?version=<commit>` |
| `purge` | yes: `POST $DOIP/doip/purge/<QID>` |
| `update` (write a component) | **no** -- native DOIP only |
| `invoke` (server-side workflow) | **no** -- native DOIP only |
| `hello`, `list_ops` | **no** |

If the request needs `update`, `invoke`, `hello` or `list_ops`, say that this
needs `episerve-doip-cli` (give the install line from `doip-fdo-access`,
"Before you start") and stop. Do not look for another way to write to an FDO.

## Calls

```bash
# metadata (RO-Crate / FDO record)
curl -fsS $DOIP/doip/retrieve/Q1748526042817 | jq

# version history, newest first; optional ?limit=N&include_sizes=true
curl -fsS "$DOIP/doip/versions/Q1748526042817?limit=20" | jq '.versions[] | {commit_id, timestamp_iso8601, message}'

# a component at a specific commit
curl -fsS -o ./predictions.tsv \
  "$DOIP/doip/retrieve/Q1748526042817/output/predictions.tsv?version=<commit-id>"
ls -la ./predictions.tsv

# evict the server's manifest-cache entry (low risk, still only when asked)
curl -fsS -X POST $DOIP/doip/purge/Q1748526042817
```

- Take `<commit-id>` from the `versions` output; never invent one. An unknown
  commit answers `404`.
- Component ids: the FDO `@id` without the leading `components/`, as listed by
  `jq -r '.kernel["fdo:hasComponent"][]["@id"]'` on the metadata; the path may
  contain `/`.
- Restricted datasets answer 401/403 without a signed link; report it.
- Large files: curl streams to disk; `Range` requests are supported.
- Partial reads: DuckDB can query a component in place over range requests and also accepts the pinned URL
  (`.../<component>?version=<commit-id>`); see "Reading only part of a large file" in `episerve-data-access-rest-fallback`.
- `purge` is the one write here. The gateway may require authorization for it;
  on 401/403 report it verbatim (the purge was not done).

## Verifying

Claim success only after seeing the JSON (a `versions` list, metadata) or the
file on disk with non-zero size (`ls -la`). Note that an HTTP `200` is not
enough for metadata: read the body. On failure quote the HTTP status and body;
don't report the operation as done.
