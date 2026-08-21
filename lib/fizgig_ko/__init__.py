"""Fizgig 한글화 부트스트랩.

venv의 site-packages 안에 있는 ``fizgig_ko.pth`` 한 줄이 인터프리터 시작 시 이 패키지를
import 합니다. 여기서는 아무것도 건드리지 않고, ``tkinter`` 가 import 되는 순간에만
패치를 거는 import 훅을 등록합니다. 학습 서브프로세스처럼 tkinter 를 쓰지 않는
프로세스에는 영향이 없습니다.

끄고 싶으면 환경변수 ``FIZGIG_LANG=en`` 을 설정하세요.
"""
import importlib.util
import os
import sys

__version__ = "1.0.0"
#: The Fizgig release this catalog was extracted from. Newer releases simply show any
#: new/changed English strings untranslated until the catalog is rebuilt.
__fizgig_baseline__ = "v4.2.0 (1b9a64f)"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../ko
STRINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strings")

_catalog = None


def get_catalog():
    """The loaded Catalog (loads lazily on first use)."""
    global _catalog
    if _catalog is None:
        from .catalog import load_dir
        _catalog = load_dir(STRINGS_DIR)
    return _catalog


def _patch_tkinter(module):
    from . import patch
    try:
        patch.apply(get_catalog(), module)
    except Exception:
        patch.log_error(BASE_DIR, "patch.apply")


class _TkFinder:
    """Lets the real tkinter import run, then patches the freshly executed module."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname != "tkinter":
            return None
        try:
            sys.meta_path.remove(self)
        except ValueError:
            pass
        spec = importlib.util.find_spec(fullname)
        if spec is None or spec.loader is None or not hasattr(spec.loader, "exec_module"):
            return spec
        loader = spec.loader
        orig_exec = loader.exec_module

        def exec_module(module):
            orig_exec(module)
            _patch_tkinter(module)

        try:
            loader.exec_module = exec_module
        except Exception:
            return None
        return spec


def install():
    if os.environ.get("FIZGIG_LANG", "").lower().startswith("en"):
        return
    if "tkinter" in sys.modules:
        _patch_tkinter(sys.modules["tkinter"])
        return
    if not any(isinstance(f, _TkFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _TkFinder())


try:
    install()
except Exception:
    try:
        from . import patch as _p
        _p.log_error(BASE_DIR, "install")
    except Exception:
        pass
