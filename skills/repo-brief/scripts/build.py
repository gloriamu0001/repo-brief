#!/usr/bin/env python3
"""Build a Repo Brief page from brief.json.

Usage: python3 build.py brief.json out.html [--repo-dir PATH] [--check-render] [--text reader.md]

Embeds demo images as data URIs so the page is one self-contained file,
checks term links, step indexes and repo paths, then fills assets/template.html.
--check-render opens the page with Playwright in every installed browser engine
(Chromium for Chrome and Edge, Firefox, WebKit for Safari) at 1280 and 390 px and
fails on page errors, horizontal scroll, labels spilling out of their box, pop-ups
that don't open, or pop-up text that spills or overlaps. Exits non-zero if any
check fails. WARN lines (a long page or repo map) don't fail the build.
"""
import base64, io, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")
MAX_W = 760


def embed(src, base_dirs):
    if src.startswith("data:"):
        return src, None, None
    path = next((os.path.join(d, src) for d in base_dirs if os.path.isfile(os.path.join(d, src))), None)
    if not path:
        raise SystemExit(f"image not found: {src}")
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=58, method=6)
        return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode(), im.width, im.height
    except ImportError:
        ext = os.path.splitext(path)[1].lstrip(".").lower().replace("jpg", "jpeg")
        with open(path, "rb") as f:
            return f"data:image/{ext};base64," + base64.b64encode(f.read()).decode(), None, None


def texts(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k != "src":
                yield from texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from texts(v)


MAX_MAP, MAX_WORDS = 22, 1700


def prose_words(B):
    """Words the brief writes itself; quoted lists, demos, install text and metadata are excluded."""
    skip = {"src", "path", "files", "repo", "branch", "props", "list", "use", "input", "output"}

    def walk(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in skip:
                    yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)
    return sum(len(re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", t).split()) for t in walk(B))


def tree_paths(node):
    if node.get("path"):
        yield node["path"]
    for c in node.get("children", []):
        yield from tree_paths(c)


def main():
    args = sys.argv[1:]
    repo_dir = None
    render = "--check-render" in args
    if render:
        args.remove("--check-render")
    text_path = None
    if "--text" in args:
        i = args.index("--text")
        text_path = args[i + 1]
        del args[i:i + 2]
    if "--repo-dir" in args:
        i = args.index("--repo-dir")
        repo_dir = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        raise SystemExit(__doc__)
    data_path, out_path = args
    with open(data_path) as f:
        B = json.load(f)
    base_dirs = [d for d in (repo_dir, os.path.dirname(os.path.abspath(data_path))) if d]
    errors = []

    for key in ("name", "repo", "problem", "idea", "map", "how", "why", "use"):
        if not B.get(key):
            errors.append(f"missing section: {key}")

    use = B.get("use") or {}
    if use.get("agentPrompt") and not use.get("agentTitle"):
        errors.append("use.agentTitle missing: title the prompt by what it does")

    # demo images
    demo = B.get("demo") or {}
    for it in demo.get("items", []):
        for slot in ([it.get("before"), it.get("after")] if demo.get("type") == "compare" else [it]):
            if slot and slot.get("src"):
                slot["src"], w, h = embed(slot["src"], base_dirs)
                if w:
                    slot["w"], slot["h"] = w, h
                if demo.get("type") == "compare" and not (slot.get("w") and slot.get("h")):
                    errors.append(f"compare image needs w/h (install Pillow): {it.get('label')}")

    # every [[term]] must be defined, and each defined term should be used
    terms = B.get("terms", {})
    if len(terms) > 7:
        errors.append(f"{len(terms)} concept links: keep only the repo's core concepts (at most 7), more dilute the links")
    links = re.findall(r"\[\[([a-z0-9-]+)", "\n".join(texts(B)))
    used = set(links)
    for k in sorted(used):
        if links.count(k) > 1:
            errors.append(f"term linked {links.count(k)} times, link only the first mention: [[{k}]]")
    for k in sorted(used - set(terms)):
        errors.append(f"undefined term: [[{k}]]")
    for k in sorted(set(terms) - used):
        errors.append(f"unused term: {k}")

    # code demo text is shown as-is
    if demo.get("type") == "code":
        for it in demo.get("items", []):
            for f in ("input", "output"):
                if re.search(r"\*\*|\[\[", it.get(f, "")):
                    errors.append(f"markup in code demo {it.get('label')}.{f}: it renders literally")

    # swimlane indexes
    how = B.get("how") or {}
    for i, s in enumerate(how.get("steps", [])):
        if not (0 <= s.get("lane", -1) < len(how.get("lanes", []))):
            errors.append(f"step {i + 1}: bad lane")
        if not (0 <= s.get("phase", -1) < len(how.get("phases", []))):
            errors.append(f"step {i + 1}: bad phase")

    # repo paths exist
    if repo_dir:
        root = os.path.join(repo_dir, B.get("root", "").strip("/"))
        paths = list(tree_paths(B.get("map", {})))
        paths += [f for s in how.get("steps", []) for f in s.get("files", [])]
        paths += [t["path"] for t in terms.values() if t.get("path")]
        for p in paths:
            m = re.match(r"^(.*?)(?:#L(\d+)(?:-L(\d+))?)?$", p)
            full = os.path.join(root, m.group(1).rstrip("/"))
            if not os.path.exists(full):
                errors.append(f"path not in repo: {p}")
            elif m.group(2):
                with open(full, errors="ignore") as f:
                    n = sum(1 for _ in f)
                a, b = int(m.group(2)), int(m.group(3) or m.group(2))
                if not (1 <= a <= b <= n):
                    errors.append(f"line range outside file ({n} lines): {p}")

    if errors:
        print("\n".join("FAIL " + e for e in errors))
        raise SystemExit(1)

    # length: the reader should get the gist in a minute
    n_map = sum(1 for _ in tree_paths(B.get("map", {})))
    if n_map > MAX_MAP:
        print(f"WARN repo map has {n_map} file items: keep it to about twenty, group similar siblings or drop items the workflow doesn't use")
    n_words = prose_words(B)
    if n_words > MAX_WORDS:
        print(f"WARN page has {n_words} words of written text (limit about {MAX_WORDS}): cut what doesn't help the reader understand or use the repo")

    # "ask questions" link: DeepWiki answers questions about the whole repo
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", B.get("repo", ""))
    if m and not any(p.get("k") == "questions" for p in B.get("props", [])):
        B.setdefault("props", []).append({"k": "questions", "v": f"[Ask an AI about this repo (DeepWiki)](https://deepwiki.com/{m.group(1)}/{m.group(2)})"})

    if text_path:
        with open(text_path, "w") as f:
            f.write(reader_text(B))

    with open(TEMPLATE) as f:
        page = f.read()
    title = B.get("title") or f"{B['name']} Repo Brief"
    page = page.replace("__TITLE__", title.replace("<", "&lt;"))
    page = page.replace("__BRIEF_JSON__", json.dumps(B, ensure_ascii=False).replace("</", "<\\/"))
    with open(out_path, "w") as f:
        f.write(page)
    if render:
        problems = check_render(page)
        if problems:
            print("\n".join("FAIL " + e for e in problems))
            raise SystemExit(1)
    print(f"ok: {out_path} ({len(page) // 1024} KB)")


def plain(s):
    s = re.sub(r"\[\[[a-z0-9-]+\|([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[\[([a-z0-9-]+)\]\]", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1", s)
    return s.replace("**", "").replace("`", "")


def reader_text(B):
    """Everything a reader can see on the page, pop-ups included, as plain text."""
    out, T = [f"# {B['name']}", ""], B.get("terms", {})
    out += [f"{p['k']}: {plain(p['v'])}" for p in B.get("props", [])]
    out += ["", "## Problem it solves"] + ["- " + plain(x) for x in B.get("problem", [])]
    out += ["", "## Main idea", plain(B.get("idea", ""))]
    demo = B.get("demo") or {}
    if demo.get("items"):
        out += ["", "## Demo"]
        for it in demo["items"]:
            out.append(f"### {it.get('label', '')}")
            if demo["type"] == "compare":
                out += [f"Before: {plain(it['before'].get('caption', ''))} [image]", f"After: {plain(it['after'].get('caption', ''))} [image]"]
            elif demo["type"] == "gallery":
                out.append(f"{plain(it.get('caption', ''))} [image]")
            else:
                out += [it.get("inputLabel", "Input") + ":", it.get("input", ""), it.get("outputLabel", "Output") + ":", it.get("output", "")]

    def walk(n, depth):
        kids = n.get("children", [])
        out.append("  " * depth + "- " + n["name"] + ("/" if kids and not n["name"].endswith("/") else ""))
        for x in n.get("overview", []):
            out.append("  " * (depth + 1) + "> " + plain(x))
        for c in kids:
            walk(c, depth + 1)
    out += ["", "## Repo map"]
    walk(B.get("map", {"name": ""}), 0)
    H = B.get("how") or {}
    out += ["", "## How it works", "Roles: " + ", ".join(H.get("lanes", []))]
    for pi, ph in enumerate(H.get("phases", [])):
        out.append(f"### {ph['title']}: {plain(ph['overview'])}")
        for i, st in enumerate(H.get("steps", [])):
            if st["phase"] == pi:
                flow = "; ".join(x for x in (st.get("in") and "in: " + st["in"], st.get("out") and "out: " + st["out"]) if x)
                out.append(f"{i + 1}. [{H['lanes'][st['lane']]}] {st['title']}: {plain(st.get('detail', ''))}" + (f" ({flow})" if flow else ""))
    out += ["", "## Why it works"] + ["- " + plain(x) for x in B.get("why", [])]
    U = B.get("use") or {}
    out += ["", "## How to use it", f"### {U.get('agentTitle', '')}", U.get("agentPrompt", "")]
    for e in U.get("envs", []):
        out.append(f"### {e['name']}")
        out += [f"- {c[0]}: {plain(c[1])}" for c in e["commands"]]
    out += ["", "## Pop-ups behind the linked words"]
    for k, t in T.items():
        line = f"- {t['title']}: {plain(t.get('body', ''))}"
        if t.get("kv"):
            line += " " + "; ".join(f"{a}: {plain(b)}" for a, b in t["kv"])
        if t.get("list"):
            items = t["list"]["items"]
            line += " List: " + "; ".join(f"{it.get('id', '')} {plain(it['text'])}".strip() for it in items)
        out.append(line)
    return "\n".join(out) + "\n"


RENDER_JS = """() => {
  const out = [], vis = el => el.getClientRects().length > 0;
  const over = document.documentElement.scrollWidth - innerWidth;
  if (over > 0) out.push(`page scrolls sideways by ${over}px`);
  document.querySelectorAll('.st, .tr .nm, .ph, .dtag').forEach(el => {
    if (!vis(el)) return;
    const box = el.closest('.cell, .ph, .tr, .layer') || el.parentElement;
    const r = el.getBoundingClientRect(), b = box.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 1 || r.right > b.right + 1)
      out.push(`text spills out of its box: "${el.textContent.trim().slice(0, 40)}"`);
  });
  return out;
}"""


POP_JS = """() => {
  const p = document.getElementById('pop'), pr = p.getBoundingClientRect(), out = [];
  const h = p.querySelector('h4'), title = (h && h.firstChild ? h.firstChild.textContent : '').trim().slice(0, 30);
  p.querySelectorAll('.hl div').forEach(d => {
    const b = d.querySelector('b'), s = d.querySelector('span');
    if (!b || !s || !b.textContent) return;
    const br = b.getBoundingClientRect(), sr = s.getBoundingClientRect();
    const overlap = br.right > sr.left + 1 && br.left < sr.right - 1 && br.top < sr.bottom - 1 && sr.top < br.bottom - 1;
    if (b.scrollWidth > b.clientWidth + 1 || overlap) out.push([title, 'names overlap their text', b.textContent.slice(0, 30)]);
  });
  p.querySelectorAll('*').forEach(e => {
    const r = e.getBoundingClientRect();
    if ((r.width && r.right > pr.right + 1) || (e.clientWidth && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== 'auto'))
      out.push([title, 'text spills out', e.textContent.trim().slice(0, 30)]);
  });
  return out;
}"""


def launch(p, engine):
    chrome = os.environ.get("CHROME_PATH") or next(
        (shutil.which(c) for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
    if engine == "chromium" and chrome:
        try:
            return p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        except Exception as e:
            print(f"render check: {chrome} failed to start ({str(e).splitlines()[0]}); trying Playwright's Chromium")
    return getattr(p, engine).launch()


def check_render(page):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("render check skipped: Playwright not installed")
        return []
    found, ran, missing = {}, [], []  # problem -> list of "engine width"

    def add(problem, tag):
        found.setdefault(problem, []).append(tag)

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        path = os.path.join(tmp, "page.html")
        with open(path, "w") as f:
            f.write(page)
        for engine in ("chromium", "firefox", "webkit"):
            try:
                browser = launch(p, engine)
            except Exception as e:
                missing.append(f"{engine} ({str(e).splitlines()[0][:80]})")
                continue
            ran.append(engine)
            for width in (1280, 390):
                tag = f"{engine} {width}px"
                pg = browser.new_page(viewport={"width": width, "height": 900})
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto("file://" + path)
                pg.wait_for_timeout(400)
                for e in errs + pg.evaluate(RENDER_JS):
                    add(e, tag)
                pops = {}  # (pop-up, kind) -> names
                for sel in (".wl", ".tr.leaf", ".st"):
                    els = [e for e in pg.query_selector_all(sel) if e.is_visible()]
                    for el in (els if sel == ".wl" else els[:1]):
                        try:
                            el.click(timeout=5000)
                        except Exception:
                            add(f"could not click {sel} \"{(el.text_content() or '').strip()[:30]}\"", tag)
                            continue
                        pg.wait_for_timeout(100)
                        if not pg.evaluate("!document.getElementById('pop').hidden"):
                            add(f"pop-up did not open for {sel}", tag)
                        else:
                            for title, kind, name in pg.evaluate(POP_JS):
                                pops.setdefault((title, kind), []).append(name)
                        pg.keyboard.press("Escape")
                for (title, kind), names in pops.items():
                    names = list(dict.fromkeys(names))
                    add(f'pop-up "{title}": {len(names)} {kind}, e.g. "{names[0]}"' if kind.startswith("names")
                        else f'pop-up "{title}": {kind}: "{names[0]}"', tag)
                pg.close()
            browser.close()
    if not ran:
        print("render check skipped: no Playwright browser installed (python3 -m playwright install chromium firefox webkit)")
    elif missing:
        print(f"render check ran in {', '.join(ran)}; could not start: {'; '.join(missing)}")
    return [f"{prob} [{', '.join(tags)}]" for prob, tags in found.items()]


if __name__ == "__main__":
    main()
