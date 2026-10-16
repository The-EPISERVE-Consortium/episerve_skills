# episerve_skills

Agent skills for working with the [EPISERVE](https://github.com/The-EPISERVE-Consortium)
platform. Each skill is a `skills/<name>/SKILL.md` (Agent Skills format: `name` and
`description` frontmatter, then instructions), so the same files work in Claude Code,
Codex, pi and other agents that read `SKILL.md`.

| Skill | Use it to |
|---|---|
| [`episerve-platform-access`](skills/episerve-platform-access/SKILL.md) | check platform health, list datasets / models / model runs, read a CKAN record, download a component (latest version), trigger a model run — via the `episerve` CLI |
| [`episerve-benchmarks`](skills/episerve-benchmarks/SKILL.md) | list benchmarks, read leaderboards, get the run spec, add a model run to a leaderboard, design and finalize benchmarks — via `episerve benchmark …` (client v0.1.14 or newer) |
| [`doip-fdo-access`](skills/doip-fdo-access/SKILL.md) | native DOIP 2.0 operations on an FDO: version history, version-pinned retrieve, update, invoke, purge — via `episerve-doip-cli` |

## Requirements

The skills drive two CLIs; install them from the releases of
[`episerve_client`](https://github.com/The-EPISERVE-Consortium/episerve_client) (`episerve`, v0.1.14 or newer for benchmarks)
and [`episerve_doip_server`](https://github.com/The-EPISERVE-Consortium/episerve_doip_server)
(`episerve-doip-cli`, v0.0.5 or newer) and set the environment variables the skills list
(`EPISERVE_API_URL`, `EPISERVE_CKAN_URL`, `EPISERVE_DOIP_URL`, `EPISERVE_API_KEY`,
`DOIP_HOST`, `DOIP_PORT`, `DOIP_UPDATE_TOKEN`).

## Install

**Claude Code** (as a plugin):
```
/plugin marketplace add The-EPISERVE-Consortium/episerve_skills
/plugin install episerve-skills@episerve
```
or copy/symlink `skills/*` into `~/.claude/skills/`.

**Codex / other agents:** clone the repo and copy or symlink `skills/*` into the agent's
skills directory (see its documentation for the exact path).

**pi / Docker:** `git clone --branch <tag> <this repo>` and point `--skill` at `skills/`.
The EPISERVE AI task runner does exactly this at image build time, pinned to a tag.

## Scope

Only skills that work against the platform's public endpoints belong here. Skills that
depend on the task-runner image (output conventions, report templates, Discord/GitHub
delivery, blackboard, anything needing the ZIB-internal Prefect server) stay in
`workflow-prefect__ai-blackboard-task-runner`.

## Development

```bash
pytest tests/        # frontmatter, name == directory, no secrets
```
Release by tagging (`v0.1.0`); consumers pin the tag.
