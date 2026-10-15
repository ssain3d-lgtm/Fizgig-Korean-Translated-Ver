"""한글화 설치/제거.

  python ko/tools/install.py          설치 (멱등 — 몇 번 실행해도 안전)
  python ko/tools/install.py --remove 제거

하는 일
  1. venv/Lib/site-packages/fizgig_ko.pth  — 인터프리터 시작 시 ko/lib 를 sys.path 에 붙이고
     fizgig_ko 를 import 하는 한 줄. fizgig_ko 는 tkinter(Fizgig 7 이하 · Gizmo)와
     fizgig.web.server(Fizgig 8 이상 웹 UI)가 import 될 때만 번역 훅을 겁니다. venv 는 git 이 추적하지 않으므로 git pull 에 안전합니다.
  2. .git/info/exclude 에 /ko/ 를 추가 — git status 가 깨끗하게 유지되고, 업데이트가
     이 폴더를 절대 건드리지 않습니다. (.gitignore 는 업스트림 파일이라 손대지 않습니다.)
"""
import os
import sys
import sysconfig

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../ko
REPO = os.path.dirname(KO_DIR)
LIB = os.path.join(KO_DIR, "lib")
PTH_NAME = "fizgig_ko.pth"


def site_packages():
    # The venv python runs this script, so purelib is the venv's site-packages.
    return sysconfig.get_paths()["purelib"]


def pth_line():
    # One statement per line; a .pth line that starts with "import" is exec'd by site.py.
    # Resolved relative to the venv first, so moving the whole Fizgig folder keeps working;
    # the absolute path recorded here is the fallback, so this folder may carry any name
    # (a downloaded ZIP unpacks as "…-main") and may live outside the Fizgig folder.
    return ("import sys, os; _p = os.path.join(os.path.dirname(sys.prefix), %r, 'lib'); "
            "_p = _p if os.path.isdir(_p) else %r; "
            "(_p in sys.path) or sys.path.append(_p); "
            "__import__('fizgig_ko') if os.path.isdir(_p) else None\n"
            % (os.path.basename(KO_DIR), LIB))


def install():
    sp = site_packages()
    rel = os.path.join(os.path.dirname(os.path.abspath(sys.prefix)), os.path.basename(KO_DIR), "lib")
    if os.path.normcase(os.path.abspath(rel)) != os.path.normcase(os.path.abspath(LIB)):
        print("[안내] 이 폴더가 Fizgig 폴더 바로 아래에 있지 않습니다. 절대 경로로 설치하므로 "
              "지금은 동작하지만, Fizgig 폴더나 이 폴더를 옮기면 설치 스크립트를 다시 실행하세요.")
    path = os.path.join(sp, PTH_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(pth_line())
    print(f"[OK] {path}")

    exclude = os.path.join(REPO, ".git", "info", "exclude")
    if os.path.isdir(os.path.dirname(exclude)):
        try:
            existing = open(exclude, encoding="utf-8").read() if os.path.exists(exclude) else ""
        except Exception:
            existing = ""
        entry = "/%s/" % os.path.basename(KO_DIR)
        if entry not in existing.splitlines():
            with open(exclude, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(entry + "\n")
            print(f"[OK] {exclude} 에 {entry} 추가")
        else:
            print(f"[OK] {exclude} 이미 등록됨")

    # Smoke tests, each in a fresh interpreter (the way Fizgig will start).
    import subprocess
    failed = False

    # Fizgig 8+ (web UI): the hook must be waiting for fizgig.web.server. It cannot import the server
    # itself here (that pulls in torch), so check that the finder is registered.
    code = ("import sys, fizgig_ko; "
            "sys.exit(0 if any(type(f).__name__ == '_WebFinder' for f in sys.meta_path) else 1)")
    if subprocess.run([sys.executable, "-c", code]).returncode == 0:
        print("[OK] 웹 UI(Fizgig 8 이상) 한글화 훅 등록 확인")
    else:
        print("[실패] 웹 UI 훅이 등록되지 않았습니다. ko/ko_error.log 를 확인하세요.")
        failed = True

    # Fizgig 7 and Gizmo (Tk): only when this Python has tkinter at all.
    has_tk = subprocess.run([sys.executable, "-c", "import tkinter"], capture_output=True).returncode == 0
    if has_tk:
        code = ("import tkinter, sys; "
                "sys.exit(0 if tkinter.Misc._options.__module__ == 'fizgig_ko.patch' else 1)")
        if subprocess.run([sys.executable, "-c", code]).returncode == 0:
            print("[OK] Tk(Gizmo / Fizgig 7 이하) 한글화 훅 동작 확인")
        else:
            print("[실패] Tk 훅이 걸리지 않았습니다. ko/ko_error.log 를 확인하세요.")
            failed = True
    else:
        print("[안내] 이 Python 에는 tkinter 가 없어 Tk 쪽(Gizmo) 확인은 건너뜁니다. "
              "Fizgig 8 본체는 웹 UI 라 영향이 없습니다.")
    return 1 if failed else 0


def remove():
    path = os.path.join(site_packages(), PTH_NAME)
    if os.path.exists(path):
        os.remove(path)
        print(f"[OK] 삭제: {path}")
    else:
        print("[OK] 이미 제거되어 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(remove() if "--remove" in sys.argv else install())
