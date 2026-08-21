"""Widget-level tests: the import hook + patch must translate what is shown and
un-translate what is read back. Needs a display (Tk)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import fizgig_ko  # noqa: E402  (installs the import hook)
from fizgig_ko.catalog import Catalog  # noqa: E402

fizgig_ko._catalog = Catalog(
    {
        "Start Training": "학습 시작",
        "Update": "업데이트",
        "Auto": "자동",
        "Off": "끔",
        "Photos": "사진",
        "Clips": "클립",
        "About Fizgig": "Fizgig 정보",
        "Version {0}": "버전 {0}",
        "Image files": "이미지 파일",
        "Training": "학습",
        "Open": "열기",
    },
    log={"Training started.\n": "학습을 시작했습니다.\n"},
)

import tkinter as tk  # noqa: E402
from tkinter import ttk  # noqa: E402

_root = None


def root():
    global _root
    if _root is None:
        _root = tk.Tk()
        _root.withdraw()
    return _root


def test_hook_patched_tkinter():
    assert tk.Misc._options.__name__ == "_options"
    assert tk.Misc._options.__module__ == "fizgig_ko.patch"


def test_label_text_and_cget_roundtrip():
    lbl = tk.Label(root(), text="Start Training")
    assert lbl.tk.call(lbl._w, "cget", "-text") == "학습 시작"   # what the screen shows
    assert lbl.cget("text") == "Start Training"                    # what the code reads
    assert lbl["text"] == "Start Training"
    lbl.config(text="Update")
    assert lbl.tk.call(lbl._w, "cget", "-text") == "업데이트"
    assert lbl.cget("text") == "Update"


def test_template_in_config():
    lbl = tk.Label(root(), text="Version v1.2")
    assert lbl.tk.call(lbl._w, "cget", "-text") == "버전 v1.2"


def test_untranslated_passthrough():
    lbl = tk.Label(root(), text="Nothing here")
    assert lbl.tk.call(lbl._w, "cget", "-text") == "Nothing here"


def test_title():
    top = tk.Toplevel(root())
    top.withdraw()
    top.title("About Fizgig")
    assert top.tk.call("wm", "title", top._w) == "Fizgig 정보"
    top.destroy()


def test_stringvar_roundtrip_and_radiobutton():
    var = tk.StringVar(root(), value="Photos")
    assert var.get() == "Photos"
    assert root().tk.globalgetvar(var._name) == "사진"
    rb = tk.Radiobutton(root(), text="Clips", variable=var, value="Clips")
    rb.invoke()
    assert root().tk.globalgetvar(var._name) == "클립"
    assert var.get() == "Clips"
    var.set("Photos")
    assert root().tk.globalgetvar(var._name) == "사진"


def test_combobox_values_and_get():
    var = tk.StringVar(root())
    cb = ttk.Combobox(root(), textvariable=var, values=["Auto", "Off", "cuda"])
    shown = cb.tk.splitlist(cb.tk.call(cb._w, "cget", "-values"))
    assert shown == ("자동", "끔", "cuda")
    cb.current(1)
    assert var.get() == "Off"
    assert cb.get() == "Off"
    cb.current(2)
    assert cb.get() == "cuda"


def test_notebook_tab_text():
    nb = ttk.Notebook(root())
    f = tk.Frame(nb)
    nb.add(f, text="Training")
    assert nb.tab(f, "text") == "학습"


def test_menu_label():
    m = tk.Menu(root(), tearoff=0)
    m.add_command(label="Open")
    assert m.entrycget(0, "label") == "열기"


def test_listbox_roundtrip():
    lb = tk.Listbox(root())
    lb.insert(tk.END, "Auto", "plain")
    assert lb.tk.call(lb._w, "get", 0) == "자동"
    assert lb.get(0) == "Auto"
    assert lb.get(0, 1) == ("Auto", "plain")


def test_text_log_only():
    t = tk.Text(root())
    t.insert(tk.END, "Training started.\n")
    t.insert(tk.END, "Start Training")       # UI catalog also applies to logs
    t.insert(tk.END, "Describe this image")  # unknown → untouched
    assert t.get("1.0", tk.END) == "학습을 시작했습니다.\n학습 시작Describe this image\n"


def test_entry_untouched_for_user_data():
    e = tk.Entry(root())
    e.insert(0, "1e-4")
    assert e.get() == "1e-4"


def test_combobox_set_direct():
    cb = ttk.Combobox(root(), values=["Auto", "Off"])
    cb.set("Auto")
    assert cb.tk.call(cb._w, "get") == "자동"
    assert cb.get() == "Auto"
    cb.set("1e-4")
    assert cb.get() == "1e-4"


def test_filetypes_translated():
    import tkinter as _tk
    w = root()
    opts = _tk.Misc._options(w, {"title": "Open", "filetypes": (("Image files", "*.png *.jpg"), ("All", "*"))})
    assert opts[1] == "열기"
    assert "이미지 파일" in str(opts[3])
