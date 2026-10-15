"""Fizgig 8+ 웹 UI 의 번역 대상 문구를 뽑는다.

  python tools/extract_web.py [--fizgig PATH]

  → work/web_candidates.json   뽑힌 문구 전부  {영어: {"src": [...], "n": 횟수}}
  → work/web_missing.json      사전(strings_web + 기존 Tk 번역 재사용)에 아직 없는 것
  → work/web_reuse.json        Tk 사전에서 그대로 가져올 수 있는 번역 (병합 시 strings_web 에 들어감)

출처 (화면에 실제로 나오는 것만 보려고 노력하지만, 헐거운 쪽으로 틀립니다 — 안 쓰이는 문구가 섞여도
번역해서 해가 될 것은 없고, 빠진 문구는 tools/harvest_web.py 가 실제 화면에서 잡아냅니다):
  html     static/index.html 의 텍스트 노드와 title/placeholder/alt/aria-label/label 속성
  js       static/app.js 의 문자열 (tools/js_strings.js 가 acorn 으로 파싱: 이어 붙인 문자열은 하나로)
  schema   서버가 /api/schema 로 내려보내는 폼(라벨, 도움말, 선택지, 모델 안내 …)
  python   서버가 화면으로 내보내는 메시지: web/*.py 의 응답 키("error" "message" "line" …)와
           web/ · families/ 의 raise 메시지, return 문구, problems/errors/notes.append(...)
  runtime  tools/harvest_web.py 가 모은 실제 화면 문구(work/web_runtime.json, 있을 때만)

필요: node + `cd tools && npm install` (acorn). Fizgig 의 torch 등이 없으면 sandbox_stubs 가 대신합니다.
"""
import argparse
import difflib
import html.parser
import json
import os
import re
import subprocess
import sys

KO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(KO_DIR, "work")
STRINGS = os.path.join(KO_DIR, "lib", "fizgig_ko", "strings")
STRINGS_WEB = os.path.join(KO_DIR, "lib", "fizgig_ko", "strings_web")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_LETTERS = re.compile(r"[A-Za-z]")

# -- 문구인지 가늠하기 ---------------------------------------------------------------------------------------
_SKIP_CALLS = {"querySelector", "querySelectorAll", "getElementById", "closest", "matches", "setAttribute",
               "getAttribute", "removeAttribute", "hasAttribute", "addEventListener", "removeEventListener",
               "add", "remove", "toggle", "contains", "getItem", "setItem", "removeItem", "fetch", "api",
               "postForm", "createElement", "createElementNS", "append", "startsWith", "endsWith", "includes",
               "indexOf", "split", "join", "replace", "replaceAll", "test", "match", "RegExp", "parse", "stringify",
               "padStart", "padEnd", "has", "get", "set", "delete", "dispatchEvent", "Event", "CustomEvent",
               "toFixed", "toLocaleString", "toLocaleDateString", "localeCompare", "log", "warn", "error",
               "getComputedStyle", "getPropertyValue", "setProperty", "open", "fillStyle", "font", "createLinearGradient",
               "addColorStop", "postMessage", "encodeURIComponent", "decodeURIComponent", "String", "Number", "Date",
               "Intl", "NumberFormat", "DateTimeFormat", "requestAnimationFrame", "setTimeout", "setInterval",
               "preventDefault", "stopPropagation", "sort", "filter", "map", "find", "some", "every", "reduce"}
_SKIP_PROPS = {"class", "className", "id", "type", "name", "href", "src", "style", "for", "value", "key", "role",
               "method", "target", "rel", "accept", "autocomplete", "inputmode", "pattern", "step", "min", "max",
               "width", "height", "viewBox", "d", "fill", "stroke", "transform", "x", "y", "cx", "cy", "r",
               "tag", "kind", "mode", "side", "fmt", "view", "tab", "field", "state", "dir", "color", "cursor",
               "display", "position", "font", "icon", "emoji_name", "mime", "ext", "url", "path", "file", "filename"}
_SKIP_ASSIGN = {"className", "id", "type", "value", "href", "src", "cssText", "display", "visibility", "width",
                "height", "name", "htmlFor", "rel", "target", "accept", "autocomplete", "min", "max", "step",
                "dataset", "fillStyle", "strokeStyle", "font", "textAlign", "textBaseline", "location", "hash",
                "search", "cursor", "color", "background", "opacity", "transform", "innerHTMLSkip"}
_UI_PROPS = {"text", "title", "placeholder", "label", "alt", "textContent", "innerText", "innerHTML",
             "message", "msg", "say", "status", "hint", "note", "caption", "heading", "tooltip", "tip", "help",
             "desc", "description", "subtitle", "summary", "empty", "none", "running", "done", "failed", "stopped",
             "queued", "paused", "ready", "idle", "busy"}


# real HTML only: "<Picture 1>" / "<name>-step<step>" in a message are text the page shows as written
_HTML_TAG = re.compile(r"</?(?:b|i|u|em|strong|code|kbd|a|br|span|small|p|ul|ol|li|div|img|button|sup|sub|"
                       r"h[1-6]|label|select|option|input|table|tr|td|th)(?:\s[^>]*)?/?>", re.I)


def _looks_like_prose(s):
    t = s.strip()
    if not _LETTERS.search(t):
        return False
    if re.match(r"^(https?:|/api/|/|\./|#|\.|\[|<|data:|\$|\^|\*)", t) or "://" in t:
        return False
    if re.match(r"^[A-Z0-9_]+$", t):
        return False
    if re.match(r"^[\w.-]+/[\w./-]*$", t) and " " not in t and not re.match(r"^[A-Z][a-z]+/[A-Z]", t):
        return False
    if re.match(r"^[a-z][\w-]*(\s+[a-z][\w-]*)+$", t) and len(t.split()) <= 4 and not re.search(r"[.,:;!?…]", t):
        return False                                   # "btn btn-sm": a class list
    if re.match(r"^[a-z][\w-]*$", t) or re.match(r"^[a-zA-Z]+[A-Z]\w*$", t) and " " not in t:
        return False                                   # an identifier
    return True


def _js_is_ui(item):
    s, ctx, kind = item["s"], item["ctx"], item["kind"]
    if "\n" in s.strip() and len(s) > 600:
        return False
    head, _, tail = ctx.partition(":")
    name = tail
    if head.startswith("arg") and name in _SKIP_CALLS:
        return False
    if head == "prop":
        if name in _SKIP_PROPS:
            return False
        if name in _UI_PROPS:
            return bool(_LETTERS.search(s))
    if head == "assign":
        if name in _SKIP_ASSIGN:
            return False
        if name in _UI_PROPS:
            return bool(_LETTERS.search(s))
    if head in ("cmp", "case"):
        return False
    if head == "key":
        return bool(re.search(r"\s", s) or re.match(r"^[A-Z][a-z]", s)) and _looks_like_prose(s)
    return _looks_like_prose(s)


# -- 출처별 추출 -----------------------------------------------------------------------------------------------
class _Text(html.parser.HTMLParser):
    ATTRS = ("title", "placeholder", "alt", "aria-label", "label")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "textarea", "pre"):
            self.skip += 1
        for k, v in attrs:
            if k in self.ATTRS and v and _LETTERS.search(v):
                self.items.append((v, f"attr:{k}"))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "textarea", "pre") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and _LETTERS.search(data):
            self.items.append((data, "text"))


def _collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def html_items(text):
    p = _Text()
    p.feed(text)
    return p.items


def from_html(static):
    with open(os.path.join(static, "index.html"), encoding="utf-8") as f:
        for s, kind in html_items(f.read()):
            yield _collapse(s), f"html:{kind}"


def from_js(static):
    tool = os.path.join(KO_DIR, "tools", "js_strings.js")
    r = subprocess.run(["node", tool, os.path.join(static, "app.js")], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise SystemExit("tools/js_strings.js 실패 (cd tools && npm install 을 했나요?)\n" + r.stderr[-800:])
    for item in json.loads(r.stdout):
        s = item["s"]
        if _HTML_TAG.search(s):
            # an HTML fragment: what reaches the screen is its text nodes and attributes
            for t, kind in html_items(s):
                if t.strip():
                    yield _collapse(t) if kind == "text" else t.strip(), f"js:html:{kind}"
            continue
        if _js_is_ui(item):
            yield ((s.strip() if "\n" in s.strip() else _collapse(s)), f"js:{item['kind']}:{item['ctx'] or '-'}",
                   item.get("plural") or [])


_SCHEMA_SKIP_KEYS = {"key", "repo", "default", "source", "name", "arch_id", "lora_name_suffix", "pref_key",
                     "aliases", "setting", "url", "path", "file", "filename", "id", "kind", "type", "media",
                     "value", "values", "suffix", "prefix", "dir", "folder", "env", "var", "unit", "format",
                     "min", "max", "step", "regime", "mode", "model", "family", "fam"}


def from_schema(fizgig_root):
    sys.path.insert(0, os.path.join(fizgig_root, "src"))
    # fizgig.py at the repo root shadows the fizgig package when the cwd is the root
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    try:
        try:
            import torch  # noqa: F401
        except Exception:
            import sandbox_stubs
            sandbox_stubs.install()
        from fizgig.web.schema import get_schema
        data = {}
        for ref in (False, True):          # the reference-DiT variant adds rows
            data[ref] = get_schema(ref_dit_set=ref)
    finally:
        os.chdir(cwd)

    def walk(o, key=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from walk(v, k)
        elif isinstance(o, (list, tuple)):
            for v in o:
                yield from walk(v, key)
        elif isinstance(o, str) and key not in _SCHEMA_SKIP_KEYS and _looks_like_prose(o):
            yield o, f"schema:{key}"
    for ref, d in data.items():
        for s, src in walk(d):
            yield (s.strip() if "\n" in s.strip() else _collapse(s)), src



_PY_KEYS = {"error", "line", "message", "summary", "name", "label", "confirm", "start", "hint", "note", "title",
            "status", "text", "detail", "warning", "msg", "reason", "description", "help", "tip", "caption",
            "placeholder", "problem", "verdict", "body", "subtitle", "done", "failed", "stopped", "running"}
_PY_APPEND_TARGETS = {"problems", "errors", "warnings", "notes", "msgs", "messages", "lines", "hints", "issues"}


_AGREEMENT = {"", "s", "es", "ies", "y", " has", "s have", " is", "s are", " was", "s were", " it", " them", "'s"}


def _py_text(n, plural=None, counter=None):
    """A string / f-string / "a" + x + "b" as text with {n} placeholders, else None. Placeholders that are
    English number agreement (`{'s' if n != 1 else ''}`) are appended to `plural`. `counter` numbers the
    placeholders across the whole expression (a "+" chain shares one count)."""
    import ast
    if counter is None:
        counter = [0]
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        parts = []
        for v in n.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                e = getattr(v, "value", None)
                if (plural is not None and isinstance(e, ast.IfExp) and isinstance(e.body, ast.Constant)
                        and isinstance(e.orelse, ast.Constant) and e.body.value in _AGREEMENT
                        and e.orelse.value in _AGREEMENT and e.body.value != e.orelse.value):
                    plural.append(counter[0])
                parts.append("{%d}" % counter[0])
                counter[0] += 1
        return "".join(parts)
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        a = _py_text(n.left, plural, counter)
        b = _py_text(n.right, plural, counter)
        if a is None and b is None:
            return None
        if a is None:
            a = "{%d}" % counter[0]
            counter[0] += 1
        if b is None:
            b = "{%d}" % counter[0]
            counter[0] += 1
        return a + b
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "format":
        base = _py_text(n.func.value)
        if base is not None:
            def sub(m):
                v = "{%d}" % counter[0]
                counter[0] += 1
                return v
            return re.sub(r"\{[^{}]*\}", sub, base)
    return None


def from_python(fizgig_root):
    import ast
    base = os.path.join(fizgig_root, "src", "fizgig")
    for sub, keys_too in (("web", True), ("families", False)):
        d = os.path.join(base, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for n in ast.walk(tree):
                cands = []
                if keys_too and isinstance(n, ast.Dict):
                    for k, v in zip(n.keys, n.values):
                        if isinstance(k, ast.Constant) and k.value in _PY_KEYS:
                            cands.append((v, f"py:{k.value}"))
                elif isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and n.exc.args:
                    cands.append((n.exc.args[0], "py:raise"))
                elif isinstance(n, ast.Return) and n.value is not None:
                    v = n.value
                    if isinstance(v, ast.Tuple) and v.elts:        # return (f"≈ {total:,} tokens …", over)
                        v = v.elts[0]
                    cands.append((v, "py:return"))
                elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
                      and isinstance(n.func.value, ast.Name) and n.func.value.id in _PY_APPEND_TARGETS and n.args):
                    cands.append((n.args[0], "py:append"))
                for node, src in cands:
                    plural = []
                    t = _py_text(node, plural)
                    if t and _looks_like_prose(t) and (" " in t.strip() or re.match(r"^[A-Z]", t.strip())):
                        yield (t.strip() if "\n" in t.strip() else _collapse(t)), src, plural


_NUMERIC = re.compile(r"[\d\s.,/:×x·%+\-–]*(?:GB|MB|MP|min|s|h|fps)?[\d\s.,/:×x·%+\-–]*(?:GB|MB|MP|min|s|h)?")


def from_runtime():
    path = os.path.join(WORK, "web_runtime.json")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for kind in ("text", "attr"):
        for s in data.get(kind, {}):
            if not re.search(r"[A-Za-z]{3}", s) or "MagicMock" in s or "fizgig_copy_" in s or re.search(r"[가-힣]", s):
                continue                                  # no words / a mock / our temp copy's path / already Korean
            if _NUMERIC.fullmatch(s.strip()):
                continue                                  # "0.6 / 15.7 GB"
            yield (s.strip() if "\n" in s.strip() else _collapse(s)), f"runtime:{kind}"

# -- 사전과 대조 -----------------------------------------------------------------------------------------------
def _load_dir(path, skip_log=True):
    out = {}
    if os.path.isdir(path):
        for fn in sorted(os.listdir(path)):
            if fn.endswith(".json"):
                with open(os.path.join(path, fn), encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    out.update(d)
    return out


def _engine_covered(keys, web):
    """The candidates that web_ko.js already turns into something else with the catalog as it is now
    (exact entries, templates, trailing punctuation, " · " pieces): nothing left to translate there."""
    import tempfile
    runner = os.path.join(KO_DIR, "lib", "fizgig_ko", "web_ko.js")
    js = ("const fs=require('fs');const [c,p,j]=process.argv.slice(2);"
          "globalThis.__KO_CAT={m:JSON.parse(fs.readFileSync(c,'utf8'))};require(j);"
          "const k=JSON.parse(fs.readFileSync(p,'utf8'));"
          "process.stdout.write(JSON.stringify(k.map(s=>__ko.trDom(s))));")
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, data in (("cat.json", web), ("keys.json", keys)):
            path = os.path.join(d, name)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            paths.append(path)
        script = os.path.join(d, "run.js")
        with open(script, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run(["node", script, *paths, runner], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return set()
    out = json.loads(r.stdout)
    return {k for k, o in zip(keys, out) if o != k}


def _keep_english():
    """tools/web_keep_english.json: what is deliberately left untranslated -> predicate."""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_keep_english.json"), encoding="utf-8") as f:
        data = json.load(f)
    exact = set(data.get("exact", []))
    pats = [re.compile(p) for p in data.get("patterns", [])]
    return lambda s: s in exact or any(p.fullmatch(s) for p in pats)


def _norm(s):
    return re.sub(r"\s+", " ", s.strip())


def _loose(s):
    """Case- and end-punctuation-insensitive form: "Comparison sheet." == "comparison sheet"."""
    return re.sub(r"[\s.:…!?*]+$", "", _norm(s)).casefold()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fizgig", default=os.path.dirname(KO_DIR), help="Fizgig 폴더 (기본: 이 폴더의 부모)")
    args = ap.parse_args()
    root = os.path.abspath(args.fizgig)
    static = os.path.join(root, "src", "fizgig", "web", "static")
    if not os.path.isdir(static):
        raise SystemExit(f"{static} 가 없습니다 — Fizgig 8 이상의 폴더가 아닙니다.")

    cands = {}
    for gen in (from_html(static), from_js(static), from_schema(root), from_python(root), from_runtime()):
        for item in gen:
            s, src = item[0], item[1]
            if not s or not _LETTERS.search(s):
                continue
            e = cands.setdefault(s, {"src": [], "n": 0})
            e["n"] += 1
            if src not in e["src"] and len(e["src"]) < 6:
                e["src"].append(src)
            if len(item) > 2 and item[2]:                       # plural-suffix placeholders (see js_strings.js)
                e["plural"] = sorted(set(e.get("plural", [])) | set(item[2]))

    web = _load_dir(STRINGS_WEB)
    tk = _load_dir(STRINGS)                           # Tk 사전: ui.json + log.json + zz_overrides.json
    wnorm = {_norm(k) for k in web}
    tnorm = {_norm(k): v for k, v in tk.items() if v}
    tloose = {}
    for k, v in tk.items():
        if v:
            tloose.setdefault(_loose(k), []).append((k, v))

    overrides = {}
    op = os.path.join(STRINGS, "zz_overrides.json")
    if os.path.exists(op):
        with open(op, encoding="utf-8") as f:
            overrides = json.load(f)
    # the catalog the page really gets: strings_web/*.json, then the shared overrides
    keep = _keep_english()
    covered = _engine_covered(list(cands), {**web, **overrides})
    reuse, missing = {}, {}
    ph = re.compile(r"\{\d+\}")
    for s, e in cands.items():
        n = _norm(s)
        if n in wnorm or s in covered or keep(s) or keep(n):
            continue
        v = tnorm.get(n)
        if v and set(ph.findall(s)) == set(ph.findall(v)):
            reuse[s] = v
            continue
        # same words, different case / end punctuation: only when the old entries agree on one translation
        alts = {ko for k, ko in tloose.get(_loose(s), []) if set(ph.findall(k)) == set(ph.findall(s))}
        if len(alts) == 1:
            v = alts.pop()
            tail = re.search(r"[.:…!?*\s]*$", s).group(0)       # keep this string's own ending
            v = re.sub(r"[.:…!?*\s]*$", "", v) + tail
            if set(ph.findall(s)) == set(ph.findall(v)):
                reuse[s] = v
                continue
        missing[s] = e

    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "web_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(cands, f, ensure_ascii=False, indent=1)
    with open(os.path.join(WORK, "web_reuse.json"), "w", encoding="utf-8") as f:
        json.dump(reuse, f, ensure_ascii=False, indent=1)
    with open(os.path.join(WORK, "web_missing.json"), "w", encoding="utf-8") as f:
        json.dump(missing, f, ensure_ascii=False, indent=1)
    print(f"후보 {len(cands)}개 → 웹 사전에 이미 있음 {len(cands) - len(reuse) - len(missing)}, "
          f"Tk 번역 재사용 {len(reuse)}, 새로 번역 {len(missing)}")
    by = {}
    for s in missing:
        k = missing[s]["src"][0].split(":")[0] + ":" + (missing[s]["src"][0].split(":")[1] if ":" in missing[s]["src"][0] else "")
        by[k] = by.get(k, 0) + 1
    for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:12]:
        print(f"   {k:28} {v}")


if __name__ == "__main__":
    main()
