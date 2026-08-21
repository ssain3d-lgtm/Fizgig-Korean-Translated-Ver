"""UI 문자열 후보 추출기.

  python ko/tools/extract.py            → ko/work/candidates.json (+ 콘솔 요약)
  python ko/tools/extract.py --missing  → 아직 번역되지 않은 문구만 ko/work/missing.json

업스트림 업데이트 뒤에 --missing 으로 새로 생긴 영어 문구를 뽑아 번역을 추가하면 됩니다.

후보 항목 형식:  { "영어 원문": {"ctx": ["kw:text@gizmo.py:120", ...], "log": true|false} }
  * f-string / "+" 연결 / .format / % 포맷은 {0} {1} 자리표시자를 가진 템플릿으로 바뀝니다.
  * log=true 인 문구는 콘솔/로그 창(Text 위젯)에만 적용되는 log.json 으로 들어갑니다.
"""
import ast
import json
import os
import re
import sys

KO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(KO_DIR)
SOURCES = ["lora_trainer_gui.py", "gizmo.py"]
STRINGS_DIR = os.path.join(KO_DIR, "lib", "fizgig_ko", "strings")
WORK = os.path.join(KO_DIR, "work")

# keyword arguments whose value is shown on screen
TEXT_KW = {"text", "label", "title", "message", "detail", "prompt", "tip", "hint", "value",
           "onvalue", "offvalue", "initialvalue", "subtitle", "desc", "description", "caption",
           "placeholder", "values", "accelerator", "default_text"}
# keyword arguments that are never UI text
SKIP_KW = {"state", "cursor", "relief", "anchor", "side", "fill", "justify", "font", "bg", "fg",
           "background", "foreground", "activebackground", "activeforeground", "highlightbackground",
           "highlightcolor", "insertbackground", "selectbackground", "selectforeground", "style",
           "orient", "mode", "encoding", "errors", "name", "key", "sep", "end", "file", "mode_",
           "wrap", "compound", "sticky", "image", "command", "variable", "textvariable", "width",
           "height", "padx", "pady", "ipadx", "ipady", "borderwidth", "bd", "troughcolor",
           "disabledforeground", "readonlybackground", "validate", "validatecommand", "show",
           "tag", "tags", "column", "columns", "iid", "creationflags", "cwd", "dtype", "device",
           "exist_ok", "newline", "format", "fmt", "suffix", "prefix", "extension", "ext", "tearoff",
           "pattern", "regex", "lang", "language", "task", "model", "repo_id", "filename",
           "selectmode", "activestyle", "exportselection", "takefocus", "class_", "className",
           "sashrelief", "handlepad", "tabs", "xscrollcommand", "yscrollcommand", "undo",
           "insertwidth", "spacing1", "spacing2", "spacing3", "lmargin1", "lmargin2", "offset",
           "overstrike", "underline", "slant", "weight", "family", "size", "rowheight",
           "fieldbackground", "bordercolor", "lightcolor", "darkcolor", "arrowcolor", "gripcount",
           "from_", "to", "resolution", "increment", "length", "sliderlength", "tickinterval",
           "indicatoron", "selectcolor", "offrelief", "overrelief", "type", "icon", "parent",
           "defaultextension", "initialdir", "initialfile", "mustexist"}
# calls whose positional string args are shown on screen (index None = all)
UI_CALLS = {"showinfo": None, "showerror": None, "showwarning": None, "askyesno": None,
            "askyesnocancel": None, "askokcancel": None, "askquestion": None, "askretrycancel": None,
            "askstring": None, "askinteger": None, "askfloat": None, "title": (0,), "wm_title": (0,),
            "set": (0,), "ToolTip": (1,), "add_command": None, "add_checkbutton": None,
            "add_radiobutton": None, "add_cascade": None, "heading": None,
            "_start_section_card": None, "_add_pref_row": None, "_add_tab_banner": None,
            "_card": None, "_button": None, "_add_field_to_section": None, "_krea2_pref": None,
            "heading": None, "para": None, "link": None, "_hint": None, "_row": None, "_label": None,
            "_add_row": None, "_section": None, "_field": None, "_check": None, "_tip": None,
            "_note": None, "_banner": None, "_step": None, "_pill": None, "_choice": None,
            "create_text": None, "itemconfigure": None, "itemconfig": None, "configure": None,
            "config": None, "StringVar": None, "OptionMenu": None}
# calls whose string args are console/log lines
LOG_CALLS = {"update_console", "_append_global_log", "update_caption_log", "_log", "_log_line",
             "_console", "_append_log", "_append_console", "log", "_status_log", "append_log"}
LOG_RECV = re.compile(r"log|console|output|preview_text|_box|takes_box|queue_box|audio_caption", re.I)
LOG_NAME = re.compile(r"log|console", re.I)
# assignments whose whole value is data the user must see in English (reading passages for
# voice recording, shell snippets, …) — never translated
EXCLUDE_ASSIGN = {"SENTENCE_CATEGORIES", "HARVARD_SENTENCES"}
# calls whose args are never UI
SKIP_CALLS = {"get", "getattr", "hasattr", "setattr", "bind", "unbind", "startswith", "endswith",
              "join", "split", "rsplit", "replace", "strip", "lstrip", "rstrip", "trace_add",
              "trace", "decode", "encode", "environ", "getenv", "isinstance", "format_map",
              "compile", "match", "search", "sub", "findall", "finditer", "fullmatch", "splitlist",
              "pop", "setdefault", "lower", "upper", "count", "find", "index", "column", "tag_config",
              "tag_configure", "tag_add", "tag_remove", "tag_bind", "bind_all", "event_generate",
              "option_add", "winfo_children", "nametowidget", "register", "call", "eval", "exec",
              "after", "mark_set", "see", "yview", "xview", "delete", "open", "exists", "isfile",
              "isdir", "makedirs", "remove", "rename", "splitext", "basename", "dirname", "abspath",
              "expanduser", "normpath", "realpath", "relpath", "glob", "iglob", "walk", "listdir",
              "run", "Popen", "check_output", "check_call", "load", "loads", "dump", "dumps",
              "_git", "_git_ok", "_get_path", "_check_num", "_persist", "_pref", "_setting",
              "map", "layout", "element_create", "theme_use", "theme_create", "geometry",
              "wm_geometry", "minsize", "maxsize", "iconbitmap", "iconphoto", "protocol",
              "wm_protocol", "wm_attributes", "attributes", "focus_set", "grid", "pack", "place",
              "grid_columnconfigure", "grid_rowconfigure", "columnconfigure", "rowconfigure",
              "add_argument", "add_parser", "set_defaults", "getboolean", "getint", "getfloat",
              "endswith", "write", "print", "warn", "warning", "error", "info", "debug", "exception",
              "sleep", "Thread", "Event", "Lock", "partial", "lambda", "translate", "maketrans",
              "zfill", "ljust", "rjust", "center", "casefold", "isdigit", "isalpha", "removeprefix",
              "removesuffix", "issubset", "union", "intersection", "difference", "update", "extend",
              "Image", "ImageTk", "PhotoImage", "Font", "nametofont", "families", "measure",
              "metrics", "actual", "cget", "entrycget", "tab", "item", "identify", "identify_row",
              "identify_column", "bbox", "selection_set", "selection", "focus", "winfo_exists",
              "__getitem__", "__setitem__", "keys", "values", "items", "append_trace"}

URL_RE = re.compile(r"^\s*(https?://|www\.|ftp://)", re.I)
PATH_RE = re.compile(r"^[A-Za-z]:\\|^\\\\|^/[\w.-]+/|^[\w.-]+/[\w.-]+$|^\.\.?/|\.(py|pyw|exe|bat|sh|json|toml|safetensors|txt|png|jpg|jpeg|webp|mp4|wav|mp3|html|css|js|pth|ckpt|bin|pt|log|csv|md|yaml|yml)$", re.I)
TECHY_RE = re.compile(r"^[\w./:@%+*=\-\[\]\\|<>#$~^,;'\"(){}?!&]*$")          # no spaces
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CODEISH_RE = re.compile(r"(<\w+[ >/]|</\w+>|\{\s*\"|\bfunction\b|\bvar\b|=>|\breturn\b|;\s*$|\bdef\b|\bimport\b|--?[a-z_]+=|\\\.|\.\*|\[\^|\$\{|\blocalStorage\b|\bdocument\.)", re.I)
SECTION_RE = re.compile(r"^\[[\w.\[\]]+\]$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
EVENT_RE = re.compile(r"^<.*>$")
TTK_STYLE_RE = re.compile(r"^([\w{}]+\.)*T[A-Z]\w*(\.\w+)*$|^(Treeview|Listbox|Entry|Text|Label|Button|Frame)(\.\w+)*$")
LOWER_IDENT_RE = re.compile(r"^[a-z][a-z0-9_\-]*$")


def never_ui(t):
    """Identifiers, ttk style names, font names, all-caps constants."""
    return bool(TTK_STYLE_RE.match(t) or LOWER_IDENT_RE.match(t)
                or (IDENT_RE.match(t) and t.isupper())
                or t in {"Consolas", "Arial", "Segoe UI", "RGBA", "RGB", "True", "False", "None"})


def looks_like_prose(s):
    t = s.strip()
    if not t or not re.search(r"[A-Za-z]{2,}", t):
        return False
    if URL_RE.search(t) or HEX_RE.match(t) or EVENT_RE.match(t) or SECTION_RE.match(t):
        return False
    if PATH_RE.search(t) and " " not in t:
        return False
    if CODEISH_RE.search(t):
        return False
    return " " in t


def looks_like_ui_token(s):
    """Single token / short phrase that can still be a UI label ('Auto', 'Off', 'French')."""
    t = s.strip()
    if not t or len(t) > 40 or IDENT_RE.match(t) and (t.isupper() or "_" in t):
        return False
    if not re.search(r"[A-Za-z]{2,}", t) or URL_RE.search(t) or HEX_RE.match(t) or EVENT_RE.match(t):
        return False
    if PATH_RE.search(t) or CODEISH_RE.search(t) or t.startswith("-"):
        return False
    if TTK_STYLE_RE.match(t) or LOWER_IDENT_RE.match(t):
        return False
    return True


def capitalised_word(s):
    t = s.strip()
    return bool(re.match(r"^[A-Z][A-Za-z]+([ \-/&+][A-Za-z0-9]+)*\.?$", t)) and len(t) >= 3


class Extractor:
    def __init__(self):
        self.out = {}     # en -> {"ctx": [...], "log": bool}

    def add(self, s, ctx, log=False):
        if not isinstance(s, str):
            return
        if not re.search(r"[A-Za-z]{2,}", s):
            return
        core = s.strip()
        if not core:
            return
        e = self.out.setdefault(s, {"ctx": [], "log": True})
        e["ctx"].append(ctx)
        e["log"] = e["log"] and log

    # ---- templates ---------------------------------------------------------
    @staticmethod
    def template_of(node):
        """Return (template, n_placeholders) for f-string / concat / format / % nodes, or None."""
        parts = []
        idx = [0]

        def ph():
            parts.append("{%d}" % idx[0])
            idx[0] += 1

        def walk(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                parts.append(n.value)
            elif isinstance(n, ast.JoinedStr):
                for v in n.values:
                    if isinstance(v, ast.Constant):
                        parts.append(str(v.value))
                    else:
                        ph()
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                walk(n.left)
                walk(n.right)
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str):
                s = re.sub(r"%(\(\w+\))?[-+ #0]*\d*(\.\d+)?[sdifgeEGxXorc%]",
                           lambda m: "%" if m.group(0) == "%%" else "\x00", n.left.value)
                for i, chunk in enumerate(s.split("\x00")):
                    if i:
                        ph()
                    parts.append(chunk)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "format" \
                    and isinstance(n.func.value, ast.Constant) and isinstance(n.func.value.value, str):
                s = re.sub(r"\{[^{}]*\}", "\x00", n.func.value.value.replace("{{", "\x01").replace("}}", "\x02"))
                for i, chunk in enumerate(s.split("\x00")):
                    if i:
                        ph()
                    parts.append(chunk.replace("\x01", "{").replace("\x02", "}"))
            else:
                ph()

        walk(node)
        tpl = "".join(parts)
        if idx[0] == 0:
            return tpl, 0
        # collapse adjacent placeholders ("{0}{1}") — they cannot be told apart at runtime anyway
        tpl = re.sub(r"(\{\d+\})(\{\d+\})+", lambda m: m.group(1), tpl)
        # renumber
        n = [0]
        def renum(m):
            r = "{%d}" % n[0]
            n[0] += 1
            return r
        tpl = re.sub(r"\{\d+\}", renum, tpl)
        return tpl, n[0]

    @staticmethod
    def is_stringish(n):
        return (isinstance(n, ast.Constant) and isinstance(n.value, str)) or isinstance(n, ast.JoinedStr) \
            or (isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mod))) \
            or (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "format")

    # ---- main walk ---------------------------------------------------------
    def run(self, path):
        fname = os.path.basename(path)
        tree = ast.parse(open(path, encoding="utf-8").read())
        parents = {}
        for node in ast.walk(tree):
            for ch in ast.iter_child_nodes(node):
                parents[ch] = node

        def consider(node, ctx, strong, log=False):
            """node: string-ish expression. strong: context known to be UI text."""
            if not self.is_stringish(node) or id(node) in excluded:
                return
            tpl, nph = self.template_of(node)
            if tpl is None:
                return
            core = re.sub(r"\{\d+\}", "", tpl).strip()
            if not core or not re.search(r"[A-Za-z]{2,}", core):
                return
            if nph and not re.search(r"[A-Za-z]{2,}", core):
                return
            if never_ui(core):
                return
            if strong:
                if looks_like_prose(tpl) or looks_like_ui_token(core) or capitalised_word(core):
                    self.add(tpl, f"{ctx}@{fname}:{node.lineno}", log)
            else:
                if looks_like_prose(tpl) or (core.endswith(":") and capitalised_word(core[:-1].strip())):
                    self.add(tpl, f"{ctx}@{fname}:{node.lineno}", log)

        seen = set()
        excluded = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in EXCLUDE_ASSIGN for t in node.targets):
                for sub in ast.walk(node.value):
                    seen.add(id(sub))
                    excluded.add(id(sub))
        for node in ast.walk(tree):
            # keyword arguments ------------------------------------------------
            if isinstance(node, ast.keyword):
                if node.arg in SKIP_KW:
                    seen.add(id(node.value))
                    continue
                if node.arg in TEXT_KW or (node.arg and re.search(
                        r"label|text|title|hint|note|tip|desc|message|subtitle|heading|caption|placeholder|prompt",
                        node.arg)):
                    v = node.value
                    if isinstance(v, (ast.List, ast.Tuple)):
                        for el in v.elts:
                            consider(el, f"kw:{node.arg}", True)
                            seen.add(id(el))
                    else:
                        consider(v, f"kw:{node.arg}", True)
                    seen.add(id(v))
                    continue
            # calls ---------------------------------------------------------------
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
                recv = ast.unparse(fn.value) if isinstance(fn, ast.Attribute) else ""
                if name in SKIP_CALLS and name not in ("configure", "config"):
                    for a in node.args:
                        seen.add(id(a))
                    continue
                if name in LOG_CALLS or LOG_NAME.search(name) or (name == "insert" and LOG_RECV.search(recv)):
                    for i, a in enumerate(node.args):
                        if name == "insert" and i == 0:
                            continue
                        consider(a, f"log:{name}", True, log=True)
                        seen.add(id(a))
                    continue
                if name == "insert":
                    # Entry/Text inserts of literal prose are data (captions, prompts) — skip
                    for a in node.args:
                        seen.add(id(a))
                    continue
                if name in UI_CALLS:
                    idxs = UI_CALLS[name]
                    for i, a in enumerate(node.args):
                        if idxs is None or i in idxs:
                            consider(a, f"call:{name}", True)
                        seen.add(id(a))
                    continue
                # unknown helper call: positional prose args count (weak); a class constructor or a
                # private helper (CollapsibleFrame("Output"), self._mk("Seed")) also takes bare labels
                helperish = bool(name) and ((name[0].isupper() and not name.isupper()) or name.startswith("_")
                                            or re.search(r"label|text|hint|row|field|card|section|button|tip|title|heading|note|badge|pill|chip|status", name, re.I))
                for a in node.args:
                    if id(a) in seen:
                        continue
                    if isinstance(a, (ast.List, ast.Tuple)):
                        continue
                    consider(a, f"call:{name}", helperish)
                    seen.add(id(a))
                continue

        # second pass: bare string literals in containers / assignments / returns (weak)
        for node in ast.walk(tree):
            if not self.is_stringish(node) or id(node) in seen:
                continue
            p = parents.get(node)
            if p is None:
                continue
            # skip pieces of a larger string-ish expression (handled at the top)
            if isinstance(p, (ast.JoinedStr, ast.FormattedValue)) or (isinstance(p, ast.BinOp) and isinstance(p.op, (ast.Add, ast.Mod))):
                continue
            if isinstance(p, ast.Call) and isinstance(p.func, ast.Attribute) and p.func.attr == "format" and p.func.value is node:
                continue
            if isinstance(p, ast.Expr):            # docstring / bare expression
                continue
            if isinstance(p, (ast.Compare, ast.Subscript, ast.keyword, ast.Call)):
                continue
            if isinstance(p, ast.Dict) and node in p.keys:
                continue
            kind = type(p).__name__
            if isinstance(p, ast.Dict):
                kind = "dict:val"
            strong = False
            if isinstance(p, (ast.List, ast.Tuple, ast.Dict)):
                tpl, _ = self.template_of(node)
                strong = capitalised_word(re.sub(r"\{\d+\}", "", tpl or ""))
            consider(node, kind, strong)

    # ---- output ---------------------------------------------------------------
    def result(self):
        return {k: {"ctx": v["ctx"][:6], "n": len(v["ctx"]), "log": v["log"]} for k, v in self.out.items()}


def load_translated():
    have = {}
    if os.path.isdir(STRINGS_DIR):
        for fn in sorted(os.listdir(STRINGS_DIR)):
            if fn.endswith(".json"):
                try:
                    have.update(json.load(open(os.path.join(STRINGS_DIR, fn), encoding="utf-8")))
                except Exception:
                    pass
    return have


def main():
    ex = Extractor()
    for src in SOURCES:
        p = os.path.join(REPO, src)
        if os.path.exists(p):
            ex.run(p)
    res = ex.result()
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    have = load_translated()
    missing = {k: v for k, v in res.items() if k not in have}
    with open(os.path.join(WORK, "missing.json"), "w", encoding="utf-8") as f:
        json.dump(missing, f, ensure_ascii=False, indent=1)
    nlog = sum(1 for v in res.values() if v["log"])
    print(f"후보 {len(res)}개 (로그 전용 {nlog}개), 이미 번역됨 {len(res) - len(missing)}개, 미번역 {len(missing)}개")
    print(f"→ {os.path.join(WORK, 'candidates.json')}\n→ {os.path.join(WORK, 'missing.json')}")


if __name__ == "__main__":
    main()
