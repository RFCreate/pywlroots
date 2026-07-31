from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F403
from setuptools.dist import Distribution

R = TypeVar("R")


def run_protocol_headers(fn: Callable[..., R]) -> Callable[..., R]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        repo_root = Path(__file__).resolve().parent
        # Run headers script to generate the protocol headers
        subprocess.run(
            [sys.executable, "protocol_headers.py", "--generate"],
            check=True,
            cwd=repo_root,
        )
        return fn(*args, **kwargs)

    return wrapper


def run_ffi_build(fn: Callable[..., R]) -> Callable[..., R]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        repo_root = Path(__file__).resolve().parent
        # Run the ffi_build.py script to generate the CFFI bindings
        subprocess.run(
            [sys.executable, "wlroots/ffi_build.py"], check=True, cwd=repo_root
        )
        Distribution.has_ext_modules = lambda self: True
        return fn(*args, **kwargs)

    return wrapper


@run_protocol_headers
@run_ffi_build
def build_wheel(*args: Any, **kwargs: Any) -> str:
    return _orig.build_wheel(*args, **kwargs)


@run_protocol_headers
@run_ffi_build
def build_editable(*args: Any, **kwargs: Any) -> str:
    return _orig.build_editable(*args, **kwargs)


@run_protocol_headers
def build_sdist(*args: Any, **kwargs: Any) -> str:
    return _orig.build_sdist(*args, **kwargs)
