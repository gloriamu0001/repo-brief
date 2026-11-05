# Repo Brief

An agent skill that turns any GitHub repo into a one-page brief you can understand in a minute, even if you don't read code.

You give it a repo URL. Your coding agent reads the code, then hands you one HTML file that answers four questions: what it does, how it does it, why it works and how to use it.

![Hallmark brief: main idea and a before/after demo](docs/images/hallmark.png)

## What's on the page

Seven sections, always in this order:

| Section | What it shows |
| --- | --- |
| Problem it solves | Who has the problem, in one or two bullets |
| Main idea | The working principle in one sentence. Its key words open the real thing, such as the actual rule list or a real example |
| Demo | Real output from the repo: a before/after slider, a gallery, or an input and its output |
| Repo map | Only the files that matter. Click one for an overview of what's inside and a link to it on GitHub |
| How it works | A swimlane of who does what, phase by phase. Each step opens its detail and the exact lines of code that do it |
| Why it works | A few one-line reasons the approach works |
| How to use it | A copy-paste prompt that has your coding agent install the tool, plus the commands |

It is one self-contained file. It reads well on a laptop and on a phone, in light and dark mode.

## Examples

| Repo | What it is | Brief |
| --- | --- | --- |
| [Nutlope/hallmark](https://github.com/Nutlope/hallmark) | Design skill that stops AI-built pages looking AI-built | [Open](https://gloriamu0001.github.io/repo-brief/hallmark.html) |
| [morluto/rea](https://github.com/morluto/rea) | MCP server and CLI that lets an agent inspect compiled apps | [Open](https://gloriamu0001.github.io/repo-brief/rea.html) |
| [cursor/plugins › pstack](https://github.com/cursor/plugins/tree/main/pstack) | Plugin of engineering playbooks for coding agents, briefed from one folder of a larger repo | [Open](https://gloriamu0001.github.io/repo-brief/pstack.html) |
| [gloriamu0001/repo-brief](https://github.com/gloriamu0001/repo-brief) | This skill, briefed by itself | [Open](https://gloriamu0001.github.io/repo-brief/repo-brief.html) |

| A step opened in How it works (REA) | A file opened in the repo map (pstack) |
| --- | --- |
| ![REA swimlane with a step pop-up](docs/images/rea.png) | ![pstack repo map with a file pop-up](docs/images/pstack.png) |

## Install

**Claude Code**, with the [skills CLI](https://github.com/vercel-labs/skills):

```sh
npx skills add gloriamu0001/repo-brief -g --agent claude-code
```

**Or as a Claude Code plugin:**

```
/plugin marketplace add gloriamu0001/repo-brief
/plugin install repo-brief@repo-brief
```

**Or by hand:** copy `skills/repo-brief/` into your agent's skills folder, for example `~/.claude/skills/repo-brief/`.

The skills CLI also installs into other agents. Replace `claude-code` with `codex`, `cursor` or `opencode`.

### Requirements

- `git` and Python 3
- [Pillow](https://pypi.org/project/Pillow/) (`python3 -m pip install Pillow`), to embed demo images in the page
- Optional: [Playwright](https://playwright.dev/python/) with Chrome or Chromium, for the layout check. Without it, that check is skipped.
- Optional: an agent that can start subagents, for the reader test. Without one, the test is skipped and the agent says so.

## Use

```
/repo-brief https://github.com/owner/repo
/repo-brief https://github.com/owner/repo/tree/main/some-folder
```

You get `<name>-repo-brief.html`. A brief takes about 20–30 minutes and roughly 400k–500k tokens. That was measured on the examples above, and it grows with the size of the repo.

## How it works

1. **Read.** The agent clones the repo and reads its code and config. The README counts as a claim and the files as the facts.
2. **Write.** Everything the page will show goes into one data file, `brief.json`, written to the content rules in [`SKILL.md`](skills/repo-brief/SKILL.md).
3. **Check.** [`build.py`](skills/repo-brief/scripts/build.py) fills a fixed template and refuses to finish while anything is wrong. It checks for missing sections, broken concept links, and file paths or line ranges that don't exist in the repo. It also opens the page in Chrome at laptop and phone width to catch layout faults.
4. **Reader test.** A fresh agent gets only the page's text and answers seven questions about the repo, marking any guesses. Every guess sends the agent back to fix that section.
5. **Deliver.** You get one HTML file.

The cloned repo is treated as untrusted. The skill reads its files and never runs its code, installers or scripts. It also ignores any agent instructions inside the repo.

## Repo layout

```
skills/repo-brief/
  SKILL.md              workflow and content rules (start here)
  reference.md          brief.json fields
  eval.md               final checks and reader-test questions
  scripts/build.py      checks, build, layout test, reader export
  assets/template.html  the page
  examples/hallmark.json
.claude-plugin/         plugin install
docs/                   example briefs, served by GitHub Pages
```

## Licence

MIT, see [LICENSE](LICENSE). Each example brief describes a third-party repo under its own licence (all MIT). The Hallmark demo images come from the Hallmark repo.
