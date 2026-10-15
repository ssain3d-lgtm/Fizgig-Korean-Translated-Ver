"""Fizgig 한글화 부트스트랩.

venv의 site-packages 안에 있는 ``fizgig_ko.pth`` 한 줄이 인터프리터 시작 시 이 패키지를
import 합니다. 여기서는 아무것도 건드리지 않고, 다음 두 모듈이 import 되는 순간에만 패치를 거는
import 훅을 등록합니다. 학습 서브프로세스처럼 둘 다 쓰지 않는 프로세스에는 영향이 없습니다.

  - ``tkinter``           — Fizgig 7 이하의 메인 창과 Gizmo (Tk 위젯 문자열을 사전으로 치환)
  - ``fizgig.web.server`` — Fizgig 8 이상의 메인 앱(웹 UI). 서버가 내보내는 페이지에 번역기를 끼움

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


def _patch_web(module):
    try:
        from . import web
        web.apply(module)
    except Exception:
        from . import web
        web.log_error("web.apply")


class _WebFinder:
    """Lets the real fizgig.web.server import run, then hooks its request handler."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname != "fizgig.web.server":
            return None
        try:
            sys.meta_path.remove(self)
        except ValueError:
            pass
        try:
            spec = importlib.util.find_spec(fullname)
        except Exception:
            return None
        if spec is None or spec.loader is None or not hasattr(spec.loader, "exec_module"):
            return spec
        loader = spec.loader
        orig_exec = loader.exec_module

        def exec_module(module):
            orig_exec(module)
            _patch_web(module)

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
    elif not any(isinstance(f, _TkFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _TkFinder())
    if "fizgig.web.server" in sys.modules:
        _patch_web(sys.modules["fizgig.web.server"])
    elif not any(isinstance(f, _WebFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _WebFinder())


try:
    install()
except Exception:
    try:
        from . import patch as _p
        _p.log_error(BASE_DIR, "install")
    except Exception:
        pass
