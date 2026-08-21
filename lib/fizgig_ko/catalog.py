"""EN → KO string catalog with exact, whitespace-tolerant and template matching.

The catalog is a plain dict {english: korean}. Keys may contain positional
placeholders ``{0}``, ``{1}`` … which match any text (including empty) at
runtime; the Korean value reuses the same placeholders in any order.

Lookups never raise: anything that is not a str, or has no translation,
comes back unchanged.
"""
import json
import os
import re

_PLACEHOLDER = re.compile(r"\{(\d+)\}")
_CACHE_MAX = 4096
# "Learning Rate:" / "Browse…" / "Save..." — the app often glues punctuation onto a label it
# built elsewhere, so a miss retries on the bare label and re-attaches the punctuation.
_TRAIL_PUNCT = re.compile(r"(\s*(?::|：|…|\.\.\.|\*|!|\?))+\s*$")
# Hints get glued together at runtime ("desc  ·  note  ·  note2", "line1\nline2"); a miss is
# retried piecewise on these separators and re-joined with the same separator.
_SEGMENT_SPLIT = re.compile(r"(\n|\s+[·|]\s+)")


def _split_ws(s):
    """'  abc\\n' -> ('  ', 'abc', '\\n')."""
    core = s.strip()
    if not core:
        return "", s, ""
    start = len(s) - len(s.lstrip())
    end = len(s.rstrip())
    return s[:start], s[start:end], s[end:]


class _Template:
    __slots__ = ("en", "ko", "regex", "prefix", "nparams", "allows_sep")

    def __init__(self, en, ko):
        self.en, self.ko = en, ko
        parts = _PLACEHOLDER.split(en)
        # parts = [lit0, idx0, lit1, idx1, ..., litN]
        pattern = ["^"]
        seen = set()
        for i, part in enumerate(parts):
            if i % 2 == 0:
                pattern.append(re.escape(part))
            else:
                if part in seen:
                    pattern.append(r"(?P=p%s)" % part)
                else:
                    seen.add(part)
                    pattern.append(r"(?P<p%s>.*?)" % part)
        pattern.append(r"\Z")
        self.regex = re.compile("".join(pattern), re.DOTALL)
        self.prefix = parts[0]
        self.nparams = len(seen)
        # A template whose own text has no line break / " · " separator must not swallow one
        # inside a placeholder — "{0} GB: {1}" would otherwise eat "16 GB: a · 24 GB: b" whole
        # and the piecewise fallback never gets a look in.
        self.allows_sep = any(_SEGMENT_SPLIT.search(parts[i]) for i in range(0, len(parts), 2))

    def apply(self, s, inner=None):
        m = self.regex.match(s)
        if not m:
            return None
        groups = m.groupdict()
        if not self.allows_sep and any(_SEGMENT_SPLIT.search(v) for v in groups.values() if v):
            return None
        if inner is not None:
            # a captured piece is often itself a UI string (f"{label}: {status}") — translate it too
            groups = {k: inner(v) for k, v in groups.items()}
        return _PLACEHOLDER.sub(lambda mm: groups.get("p" + mm.group(1), ""), self.ko)


class Catalog:
    def __init__(self, forward=None, log=None):
        self.exact = {}
        self.reverse = {}
        self.templates = []       # templates that start with a placeholder
        self.by_prefix = {}       # first 3 chars of literal prefix -> [templates]
        self.log_exact = {}
        self.log_templates = []
        self.log_by_prefix = {}
        self._cache = {}
        self._log_cache = {}
        if forward:
            self.add(forward)
        if log:
            self.add(log, log_only=True)

    # -- building -----------------------------------------------------------
    def add(self, mapping, log_only=False):
        exact = self.log_exact if log_only else self.exact
        wild = self.log_templates if log_only else self.templates
        by_prefix = self.log_by_prefix if log_only else self.by_prefix
        for en, ko in mapping.items():
            if not isinstance(en, str) or not isinstance(ko, str) or not ko:
                continue
            if _PLACEHOLDER.search(en):
                # an identity template ("{0} GB: {1}") is still useful: it lets the captured
                # pieces ("up to 0.25 MP") be translated on their own
                t = _Template(en, ko)
                if t.prefix:
                    by_prefix.setdefault(t.prefix[:3], []).append(t)
                else:
                    wild.append(t)
            elif en != ko:
                exact[en] = ko
                if not log_only:
                    self.reverse.setdefault(ko, en)
        self._cache.clear()
        self._log_cache.clear()

    # -- lookup -------------------------------------------------------------
    def _lookup(self, s, exact, by_prefix, wild, cache, depth=0):
        hit = cache.get(s)
        if hit is not None:
            return hit
        inner = None
        if depth < 3:
            def inner(v):
                if not v or len(v) > 400:
                    return v
                try:
                    return self._lookup(v, exact, by_prefix, wild, cache, depth + 1)
                except Exception:
                    return v
        out = exact.get(s)
        if out is None:
            lead, core, trail = _split_ws(s)
            if core and core != s:
                core_hit = exact.get(core)
                if core_hit is not None:
                    out = lead + core_hit + trail
            if out is None:
                for cand in (s, core):
                    if not cand:
                        continue
                    for t in by_prefix.get(cand[:3], ()):
                        r = t.apply(cand, inner)
                        if r is not None:
                            out = r if cand is s else lead + r + trail
                            break
                    if out is not None:
                        break
                    for t in wild:
                        r = t.apply(cand, inner)
                        if r is not None:
                            out = r if cand is s else lead + r + trail
                            break
                    if out is not None:
                        break
        if out is None and depth < 4:
            m = _TRAIL_PUNCT.search(s)
            if m and m.start() > 0:
                bare = s[:m.start()]
                r = self._lookup(bare, exact, by_prefix, wild, cache, depth + 1)
                if r != bare:
                    out = r + s[m.start():]
        if out is None and depth < 4:
            parts = _SEGMENT_SPLIT.split(s)
            if len(parts) > 1:
                # odd indices are the separators themselves (captured), kept verbatim
                done = [p if i % 2 or not p.strip() else self._lookup(p, exact, by_prefix, wild, cache, depth + 1)
                        for i, p in enumerate(parts)]
                if any(a != b for a, b in zip(parts, done)):
                    out = "".join(done)
        if out is None:
            out = s
        if len(cache) >= _CACHE_MAX:
            cache.clear()
        cache[s] = out
        return out

    def tr(self, s):
        """Translate a UI string (labels, titles, messages, dropdown values)."""
        if not isinstance(s, str) or not s or not self.exact and not self.templates and not self.by_prefix:
            return s
        try:
            return self._lookup(s, self.exact, self.by_prefix, self.templates, self._cache)
        except Exception:
            return s

    def tr_log(self, s):
        """Translate a console/log line: log catalog first, then the UI catalog."""
        if not isinstance(s, str) or not s:
            return s
        try:
            out = self._lookup(s, self.log_exact, self.log_by_prefix, self.log_templates, self._log_cache)
            if out is s or out == s:
                out = self.tr(s)
            return out
        except Exception:
            return s

    def untr(self, s):
        """Korean -> the original English (only for exact, non-template entries)."""
        if not isinstance(s, str) or not s:
            return s
        try:
            r = self.reverse.get(s)
            if r is not None:
                return r
            lead, core, trail = _split_ws(s)
            if core and core != s:
                r = self.reverse.get(core)
                if r is not None:
                    return lead + r + trail
        except Exception:
            pass
        return s


def load_dir(path):
    """Load every *.json in ``path`` into a Catalog. Files named log*.json feed
    the log catalog; everything else feeds the UI catalog. Later files
    (alphabetically) override earlier ones, so ``zz_overrides.json`` wins."""
    cat = Catalog()
    if not os.path.isdir(path):
        return cat
    ui, log = {}, {}
    for name in sorted(os.listdir(path)):
        if not name.lower().endswith(".json"):
            continue
        try:
            with open(os.path.join(path, name), encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        (log if name.lower().startswith("log") else ui).update(data)
    cat.add(ui)
    cat.add(log, log_only=True)
    return cat
