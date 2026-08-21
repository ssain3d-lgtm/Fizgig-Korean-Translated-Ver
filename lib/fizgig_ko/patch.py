"""Monkey-patches Tkinter so every string that reaches a widget passes through
the Korean catalog — and every string read back from a widget is mapped to its
original English, so the app's own comparisons keep working.

Forward (EN→KO) choke points
  * Misc._options           every tk widget constructor / configure / Menu.add / Canvas items /
                            messagebox / filedialog (keys: text label title message detail
                            value onvalue offvalue values filetypes)
  * ttk._format_optdict     ttk widgets, Notebook.add/tab, Treeview.heading/insert
  * Wm.wm_title / title     window titles
  * Variable.set/initialize StringVars bound to labels, dropdowns, radio buttons
  * Listbox.insert          list rows
  * Text.insert             console / log panes (log catalog only — never prompts or captions)

Reverse (KO→EN)
  * Misc.cget / __getitem__ for the same option keys
  * StringVar.get, Entry.get (Combobox/Spinbox), Listbox.get
"""
import os
import traceback

_TEXT_KEYS = ("text", "label", "title", "message", "detail", "value", "onvalue", "offvalue")
_LIST_KEYS = ("values",)
_KEYSET = frozenset(_TEXT_KEYS + _LIST_KEYS + ("filetypes",))

_applied = False


def _translate_opts(cat, cnf):
    """Return a copy of the option dict with translatable values swapped."""
    out = None
    for k in cnf:
        key = k[:-1] if k and k[-1] == "_" else k
        if key not in _KEYSET:
            continue
        v = cnf[k]
        nv = v
        if key in _TEXT_KEYS:
            if isinstance(v, str):
                nv = cat.tr(v)
        elif key == "values":
            if isinstance(v, (list, tuple)):
                nv = type(v)(cat.tr(x) if isinstance(x, str) else x for x in v)
        elif key == "filetypes":
            if isinstance(v, (list, tuple)):
                try:
                    nv = tuple((cat.tr(ft[0]),) + tuple(ft[1:]) if isinstance(ft, (list, tuple)) and ft and isinstance(ft[0], str) else ft
                               for ft in v)
                except Exception:
                    nv = v
        if nv is not v:
            if out is None:
                out = dict(cnf)
            out[k] = nv
    return cnf if out is None else out


def apply(cat, tkinter):
    """Patch the already-imported ``tkinter`` module (and its ttk submodule)."""
    global _applied
    if _applied:
        return
    _applied = True

    Misc = tkinter.Misc
    _cnfmerge = tkinter._cnfmerge

    # ---- tk widgets: constructor/configure/Menu.add/Canvas/messagebox/filedialog -----------
    _orig_options = Misc._options

    def _options(self, cnf, kw=None):
        try:
            merged = _cnfmerge((cnf, kw)) if kw else _cnfmerge(cnf)
            if isinstance(merged, dict) and merged:
                merged = _translate_opts(cat, merged)
            return _orig_options(self, merged)
        except Exception:
            return _orig_options(self, cnf, kw)

    Misc._options = _options

    # ---- reading options back --------------------------------------------------------------
    _orig_cget = Misc.cget

    def cget(self, key):
        v = _orig_cget(self, key)
        try:
            k = key[:-1] if isinstance(key, str) and key and key[-1] == "_" else key
            if k in _TEXT_KEYS and isinstance(v, str):
                return cat.untr(v)
        except Exception:
            pass
        return v

    Misc.cget = cget
    Misc.__getitem__ = cget

    # ---- window titles ---------------------------------------------------------------------
    Wm = tkinter.Wm
    _orig_title = Wm.wm_title

    def wm_title(self, string=None):
        if isinstance(string, str):
            string = cat.tr(string)
        return _orig_title(self, string)

    Wm.wm_title = wm_title
    Wm.title = wm_title

    # ---- variables -------------------------------------------------------------------------
    Variable = tkinter.Variable
    _orig_set = Variable.set

    def vset(self, value):
        if isinstance(value, str):
            value = cat.tr(value)
        return _orig_set(self, value)

    Variable.set = vset
    Variable.initialize = vset

    StringVar = tkinter.StringVar
    _orig_sget = StringVar.get

    def sget(self):
        v = _orig_sget(self)
        return cat.untr(v) if isinstance(v, str) else v

    StringVar.get = sget

    # ---- Entry / Combobox / Spinbox read-back ----------------------------------------------
    Entry = tkinter.Entry
    _orig_eget = Entry.get

    def eget(self):
        v = _orig_eget(self)
        return cat.untr(v) if isinstance(v, str) else v

    Entry.get = eget

    # ---- Listbox ---------------------------------------------------------------------------
    Listbox = tkinter.Listbox
    _orig_linsert = Listbox.insert
    _orig_lget = Listbox.get

    def linsert(self, index, *elements):
        try:
            elements = tuple(cat.tr(e) if isinstance(e, str) else e for e in elements)
        except Exception:
            pass
        return _orig_linsert(self, index, *elements)

    def lget(self, first, last=None):
        v = _orig_lget(self, first, last)
        try:
            if isinstance(v, str):
                return cat.untr(v)
            if isinstance(v, tuple):
                return tuple(cat.untr(x) if isinstance(x, str) else x for x in v)
        except Exception:
            pass
        return v

    Listbox.insert = linsert
    Listbox.get = lget

    # ---- Text: console / log panes only ----------------------------------------------------
    Text = tkinter.Text
    _orig_tinsert = Text.insert

    def tinsert(self, index, chars, *args):
        if isinstance(chars, str):
            chars = cat.tr_log(chars)
        return _orig_tinsert(self, index, chars, *args)

    Text.insert = tinsert

    # ---- ttk -------------------------------------------------------------------------------
    try:
        from tkinter import ttk
        _orig_fmt = ttk._format_optdict

        def _format_optdict(optdict, script=False, ignore=None):
            try:
                if isinstance(optdict, dict) and optdict:
                    optdict = _translate_opts(cat, optdict)
            except Exception:
                pass
            return _orig_fmt(optdict, script, ignore)

        ttk._format_optdict = _format_optdict

        # Combobox.set / Spinbox.set talk to Tcl directly, bypassing Variable.set
        for cls_name in ("Combobox", "Spinbox"):
            cls = getattr(ttk, cls_name, None)
            if cls is None or "set" not in cls.__dict__:
                continue
            _orig_cset = cls.__dict__["set"]

            def _mk(orig):
                def cset(self, value):
                    if isinstance(value, str):
                        value = cat.tr(value)
                    return orig(self, value)
                return cset
            cls.set = _mk(_orig_cset)
    except Exception:
        pass


def log_error(base_dir, where):
    try:
        with open(os.path.join(base_dir, "ko_error.log"), "a", encoding="utf-8") as f:
            f.write(f"--- {where}\n{traceback.format_exc()}\n")
    except Exception:
        pass
