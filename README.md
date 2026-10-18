# episerve_skills

Agent skills for working with the [EPISERVE](https://github.com/The-EPISERVE-Consortium)
platform. Each skill is a `skills/<name>/SKILL.md` (Agent Skills format: `name` and
`description` frontmatter, then instructions), so the same files work in Claude Code,
Codex, pi and other agents that read `SKILL.md`.

| Skill | Use it to | Risk |
|---|---|---|
| [`episerve-data-access`](skills/episerve-data-access/SKILL.md) | check health, list datasets / models / runs, read a CKAN record, list and download components (latest version) — `episerve` CLI | read-only |
| [`episerve-model-runs`](skills/episerve-model-runs/SKILL.md) | start a forecast model run, follow its status, fetch the predictions — `episerve trigger-model-run`, `list runs`, `run show` | uses cluster resources, not undoable |
| [`episerve-benchmarks`](skills/episerve-benchmarks/SKILL.md) | list benchmarks, read leaderboards, get the run spec, add a run to a leaderboard, design and finalize benchmarks — `episerve benchmark …` | writes; `finalize` is irreversible |
| [`doip-fdo-access`](skills/doip-fdo-access/SKILL.md) | native DOIP 2.0 operations on an FDO: version history, version-pinned retrieve, update, invoke, purge — `episerve-doip-cli` | writes to live FDOs |

The skills are split by task and risk: finding and fetching is read-only, everything that starts
or fixes something has its own skill with its own "only when asked" gate.

## Requirements

The skills do not talk to the platform themselves; they drive two command-line tools. The agent
runs them in its own shell, so they must be installed **and on the `PATH`** under the names the
skills use (`episerve`, `episerve-doip-cli`), and the environment variables below must be set in the
shell the agent starts from. Without them the skills just report what is missing.

### 1. Install the CLIs

Download the binary for your system from the **latest** release (always use the latest), rename it and put it on your `PATH`.

| Tool | Needed by | Release | Linux | macOS | Windows |
|---|---|---|---|---|---|
| `episerve` | `episerve-data-access`, `episerve-model-runs`, `episerve-benchmarks` | [`episerve_client`](https://github.com/The-EPISERVE-Consortium/episerve_client/releases/latest) | `episerve-client-linux` | `episerve-client-macos` | `episerve-client-windows.exe` |
| `episerve-doip-cli` | `doip-fdo-access` | [`episerve_doip_server`](https://github.com/The-EPISERVE-Consortium/episerve_doip_server/releases/latest) | `episerve-doip-cli-linux` | `episerve-doip-cli-macos` | `episerve-doip-cli-windows.exe` |

Linux / macOS:
```bash
curl -fsSL -o ~/.local/bin/episerve https://github.com/The-EPISERVE-Consortium/episerve_client/releases/latest/download/episerve-client-linux   # -macos on a Mac
curl -fsSL -o ~/.local/bin/episerve-doip-cli https://github.com/The-EPISERVE-Consortium/episerve_doip_server/releases/latest/download/episerve-doip-cli-linux   # -macos on a Mac
chmod +x ~/.local/bin/episerve ~/.local/bin/episerve-doip-cli      # ~/.local/bin must be on PATH
```

Windows (PowerShell): download the two `.exe` files, rename them to `episerve.exe` and
`episerve-doip-cli.exe`, put them in a folder on your `PATH` (e.g. `%USERPROFILE%\bin`), and open a new terminal.

### 2. Set the environment variables

Only the variables of the skills you use are needed.

| Variable | Used by | Meaning |
|---|---|---|
| `EPISERVE_API_URL` | data-access, model-runs, benchmarks | API server base URL |
| `EPISERVE_CKAN_URL` | data-access | CKAN base URL (`item show`) |
| `EPISERVE_DOIP_URL` | data-access, model-runs | DOIP HTTP gateway base URL (list / download components) |
| `EPISERVE_API_KEY` | model-runs, benchmarks (writes) | Personal bearer token, **valid for one day** (`episerve login`); the user needs the right `runs` (model runs) or `benchmarks` (benchmarks); not needed for reads |
| `EPISERVE_USERNAME`, `EPISERVE_PASSWORD` | `episerve login` | the account's email and password, so `login` needs no flags |
| `DOIP_HOST`, `DOIP_PORT` (`3567`) | doip-fdo-access | native DOIP server |
| `DOIP_UPDATE_TOKEN` | doip-fdo-access (`update` only) | write token |

Linux / macOS: add the variables to `~/.bashrc` (or `~/.zshrc`), then open a new terminal:
```bash
export EPISERVE_API_URL=<api-server-url>
export EPISERVE_CKAN_URL=<ckan-url>
export EPISERVE_DOIP_URL=<doip-http-gateway-url>
export DOIP_HOST=<doip-server-host>
export DOIP_PORT=<doip-server-port>
```
Windows PowerShell: `$env:EPISERVE_API_URL = "<api-server-url>"` for the current session, or
`setx EPISERVE_API_URL "<api-server-url>"` to keep it (takes effect in new terminals).

For the public platform use `https://api.episerve.zib.de`, `https://data.episerve.zib.de` and `https://doip.episerve.zib.de` (DOIP host `doip.episerve.zib.de`, port `3567`; `episerve-doip-cli` uses these by default, `episerve` has no default). For another deployment, ask its administrator. Set them **before** starting the agent
(Claude Code, Codex, ...), otherwise it will not see them.

Do not put `EPISERVE_API_KEY` or `DOIP_UPDATE_TOKEN` in a profile file: the API token expires after one day
(run `episerve login`, it saves the token to a `.env` file in the current directory, which `episerve` reads),
and the DOIP write token is a secret.

### 3. Check that it works

These commands are the same in every shell; run them yourself or ask the agent to:

```
episerve --cli-version        # installed and on PATH; prints the version
episerve health               # API URL set and reachable
episerve benchmark -h         # fails if the client is outdated: install the latest release
episerve-doip-cli --help      # DOIP CLI installed
```

`command not found` / `is not recognized` means the binary is not on the `PATH` (or has a different
name); an error that lists `EPISERVE_API_URL=...` means that variable is not set in the shell the
agent was started from.

### Notes on shells

The command examples inside the skills are written for a POSIX shell (`\` line continuation,
`$VAR`, `jq`, `ls -la`). On Windows, agents usually translate them (PowerShell uses `` ` ``
for continuation and `$env:VAR`); if you want fewer surprises, run the agent in WSL or Git Bash.

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
Consumers (e.g. the EPISERVE task runner image) take `main`.
