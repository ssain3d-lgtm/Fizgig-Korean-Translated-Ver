"""torch 같은 무거운 패키지가 없는 환경(CI, 클라우드 샌드박스)에서 Fizgig 의 웹 서버/스키마를 import 하기 위한 스텁.

번역 문구를 뽑고 화면을 점검하려는 것이지 학습을 돌리려는 것이 아닙니다. 진짜 패키지가 설치되어 있으면
그것을 쓰고, 없는 것만 MagicMock 모듈로 대신합니다. 사용자 PC(진짜 Fizgig venv)에서는 아무 일도 하지 않습니다.
"""
import importlib.abc
import importlib.machinery
import sys
import types
from unittest.mock import MagicMock

HEAVY = {"torch", "torchvision", "torchaudio", "bitsandbytes", "accelerate", "diffusers", "transformers",
         "tokenizers", "sentencepiece", "einops", "hqq", "comfy_kitchen", "triton", "cv2", "scipy",
         "huggingface_hub", "soundfile", "librosa", "av", "onnxruntime", "insightface", "pynvml", "webview"}


class _Mod(types.ModuleType):
    __path__ = []

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        v = MagicMock(name=f"{self.__name__}.{name}")
        setattr(self, name, v)
        return v


class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] not in HEAVY:
            return None
        for f in sys.meta_path:                      # a real installed package wins
            if f is self or not hasattr(f, "find_spec"):
                continue
            try:
                if f.find_spec(name, path, target) is not None:
                    return None
            except Exception:
                continue
        return importlib.machinery.ModuleSpec(name, self, is_package=True)

    def create_module(self, spec):
        return _Mod(spec.name)

    def exec_module(self, module):
        pass


def install():
    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.append(_Finder())
