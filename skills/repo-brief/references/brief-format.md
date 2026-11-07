# brief.json

One JSON object. `references/example-hallmark.json` is a real brief in this format, with its long rule list cut to a few items.

## Inline markup (any text field)

- `[[key|label]]` concept link; opens `terms.key`. `[[key]]` uses the term's title as the label.
- `[label](https://…)` external link
- `**bold**`, `` `code` ``

## Fields

| Field | Shape | Notes |
| --- | --- | --- |
| `name` | string | Page heading. The page title is `<name> Repo Brief`. |
| `repo` | URL | GitHub repo. File links become `<repo>/blob|tree/<branch>/<path>`. |
| `branch` | string | Default `main`. |
| `root` | string | Optional. For a folder inside a repo: its path (e.g. `pstack`). All other paths are relative to it. |
| `props` | `[{k, v, tag?}]` | Metadata rows: `type` (tag), `licence`, `version`, `source`. Type is what the reader installs or runs: agent skill, plugin, MCP server, CLI, library, web app. Source links the repo or folder and names its author. |
| `problem` | `[string]` | Bullets. |
| `idea` | string | One sentence. |
| `demo` | `{type, items}` | Optional. See below. |
| `map` | node | Repo tree. See below. |
| `how` | `{lanes, phases, steps}` | Swimlane. See below. |
| `why` | `[string]` | Bullets, `**Lead:** text`. |
| `use` | `{agentTitle, agentPrompt, envs}` | `agentTitle` names what the prompt does. `envs: [{name, commands: [[command, description]]}]`. |
| `terms` | `{key: term}` | The repo's core concepts, at most seven. Every term must be linked exactly once and every link defined; `build.py` checks both. |

### demo

- `type: "compare"`: `items: [{label, before: {src, caption}, after: {src, caption}}]`. A draggable divider over two full-page images, captions pinned to each side of it.
- `type: "gallery"`: `items: [{label, src, caption?}]`.
- `type: "code"`: `items: [{label, input, output, inputLabel?, outputLabel?}]`. Input and output are plain text shown as-is, wrapped to fit; quote them word for word without re-wrapping.

`src` is a path relative to `--repo-dir` or to the JSON file. `build.py` embeds images as data URIs at 760 px wide (needs Pillow), so the page is one self-contained file. Multiple items render as tabs.

### map

Folder: `{name, children: [node]}`. File, or a folder shown as one item: `{name, path, overview: [string]}`. For many similar siblings, one item such as `{name: "principle-*/ (24)", path: "skills", overview: [...]}`. Define a repo-specific term in the overview where it first appears.

### how

- `lanes: [string]`: roles, top to bottom.
- `phases: [{title, overview}]`: columns, left to right.
- `steps: [{phase, lane, title, detail, in?, out?, files?, script?, loop?}]`: in run order; `phase` and `lane` are 0-based indexes. `script: true` sets the title in monospace (a command). `loop: true` marks a step that repeats until it passes. `files` are repo paths; add `#L120-L180` to point at the lines that do the step. `build.py` checks the range exists.

### term

`{title, body?, path?, kv?, list?, more?}`

- `kv: [[label, value]]`: label/value rows, for a worked example or a field's allowed values.
- `list: {items: [{id, tag?, group?, text}], tones?: {tag: "bad"|"warn"|"good"}}`: a long list (rules, commands). Distinct tags become filter buttons; `group` adds subheadings.
- `more: [termKey, label]`: a link to another term from inside this one.
- `path`: a repo file shown as a link at the bottom.
