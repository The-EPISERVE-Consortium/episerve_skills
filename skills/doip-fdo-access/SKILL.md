---
name: doip-fdo-access
description: Use only when the request explicitly asks for a native DOIP-protocol operation on an FDO -- list an object's version history, retrieve a component at a specific commit, write/replace a component, invoke a server-side DOIP workflow, or purge the server's manifest cache. For platform catalog queries, CKAN records, and latest-version component downloads, use episerve-data-access instead. Not triggered by default.
---

# DOIP FDO access

Drive a running EPISERVE **DOIP server** over its native binary DOIP 2.0
protocol, using the `episerve-doip-cli` binary (a static binary from the
`episerve_doip_server` release; use the latest release).
The server is already running -- this skill only sends it requests.

Only act if the request explicitly asks for one of the operations below. If
it doesn't, do nothing in this skill.

## Which skill -- this one or `episerve-data-access`

This skill is **only** for operations that exist solely over the native DOIP
protocol. Everything else goes to `episerve-data-access`.

| You want to... | Skill |
|---|---|
| List an object's **version history** (`versions`) | **this skill** (only option) |
| Retrieve a component **at a specific commit** (`--version`) | **this skill** (only option) |
| **Write / replace** a component on an existing FDO (`update`) | **this skill** (only option) |
| **Invoke** a server-side workflow (e.g. `equation_extraction`) | **this skill** (only option) |
| `hello` / `list_ops`; purge the manifest cache | **this skill** (only option) |
| List components / download a component **at latest version** | **`episerve-data-access`** -- HTTP gateway, streamed, better for large files. Only fall back to this skill's `retrieve` if that gateway is unreachable. |
| Catalog listings, CKAN record, `health` | **`episerve-data-access`** -- none of those are DOIP operations |
| Trigger a model run | **`episerve-model-runs`** |

Rule of thumb: if you don't need a **version**, a **write**, or an
**invoke / purge / hello**, you don't need this skill -- use
`episerve-data-access`.

## Connection

Expected in the environment -- don't guess a host:

| Env var | Meaning |
|---|---|
| `DOIP_HOST` | Hostname of the DOIP server (the deployment's public host, or the in-cluster Service DNS when running inside the cluster) |
| `DOIP_PORT` | Native DOIP port -- `3567` |
| `DOIP_UPDATE_TOKEN` | Shared secret required **only** for `update`. Read directly by the CLI. Absent for read-only tasks -- that's fine. |

The server speaks **TLS-wrapped** DOIP frames, so use the CLI's default: **do
not pass `--no-tls`** (the handshake fails with "Socket closed before
receiving expected bytes"). No TLS flag at all = TLS on, certificate
verification off. Pass `--secure` only if you want verification and the
certificate matches the host you connect to (it will not for an in-cluster
Service DNS with a self-signed certificate).
If an env var needed for what the request asked is unset, that's a real
failure -- say so explicitly rather than skipping the call.

## How to call it

Always pass `--force-json-output`. In that mode the CLI prints **exactly one
JSON envelope on stdout and nothing else** (no banner, no debug logging):

```
{"action": "<action>", "object_id": "<qid|null>", "ok": true, "result": <payload>}
```

on failure:

```
{"action": "<action>", "object_id": "<qid|null>", "ok": false, "error": "<message>"}
```

and the exit code is `0` on `ok:true`, `1` on `ok:false`. Parse it with `jq`;
check `.ok` before trusting `.result`.

```bash
DOIP="episerve-doip-cli --host $DOIP_HOST --port $DOIP_PORT --force-json-output"

# metadata (all kernel blocks)
$DOIP --action retrieve --object-id Q1748526042817

# version history
$DOIP --action versions --object-id Q1748526042817

# a component at a specific commit  (--output is REQUIRED in --force-json-output mode)
$DOIP --action retrieve --object-id Q1748526042817 \
  --component output/predictions.tsv \
  --version <commit-id> --output ./predictions.tsv
```

`result` payloads: `retrieve` (metadata) -> `{"metadata_blocks": [...]}`;
`versions` -> `{"versions": [...]}`; component `retrieve` -> `{"saved_to",
"media_type", "bytes"}`; `update` / `invoke` -> `{"metadata_blocks": [...]}`;
`hello` / `list_ops` / `purge` -> the raw response object.

A component id is the FDO `fdo:hasComponent` `@id` with the leading
`components/` stripped -- e.g. `output/predictions.tsv`,
`input/config.json`. This is exactly what `episerve item list-components`
returns as `id`; take it from there or from a metadata `retrieve` rather
than hand-building it (the un-stripped `components/...` form 404s), and no
extension is added automatically. A component `retrieve` here requires
`--output` (binary content can't share stdout with the envelope); for a
plain latest-version download prefer `episerve-data-access` (it
streams).

## Reads

`hello`, `list_ops`, `retrieve` (metadata), `retrieve --component --version`,
and `versions` are safe whenever the request asks. After saving a component,
`ls -la` it to confirm non-zero size.

## `update` -- the write

Treat this like opening a PR: **only** if the request explicitly says to
update / replace / write back a component. It mutates a component on a live
FDO in lakeFS -- there is no dry-run.

```bash
$DOIP --action update --object-id Q1748526042817 \
  --component output/predictions.tsv \
  --input ./predictions.tsv --media-type text/tab-separated-values
```

- Requires `DOIP_UPDATE_TOKEN` (picked up from the env by the CLI). If it's
  unset the envelope comes back `ok:false` with an authorization error --
  report that plainly, don't skip silently and don't fabricate success.
- Pass a correct `--media-type`; the default is `application/octet-stream`.
- Confirm the returned envelope is `ok:true` before claiming success.

## `invoke` and `purge`

- `--action invoke --object-id <QID> --workflow <name> --params '<json>'`
  runs compute **on the server** -- only if the request asks for it.
- `--action purge --object-id <QID>` evicts the server's manifest-cache
  entry for that object. Low risk, but still only run it if the request asks.

## Verifying

Before your final message claims a DOIP call succeeded: confirm the envelope
on stdout was `ok:true` and carried the `result` you expected (metadata
blocks, a versions list, a saved file, an update ack). An `ok:false`
envelope, a non-zero exit, or a `ConnectionError` in `.error` is a real
failure -- quote it in your summary rather than reporting the operation as
done.
