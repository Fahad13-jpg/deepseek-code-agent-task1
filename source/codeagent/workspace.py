"""File tools restricted to a newly created project directory."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from uuid import uuid4

MAX_FILE_BYTES = 256_000
MAX_PROJECT_BYTES = 12_000_000
MAX_FILES = 300
RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def new_project(base: Path, name: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}", name):
        raise ValueError("Project name: use 1–60 letters, numbers, hyphens or underscores; start with a letter or number.")
    base = Path(base).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    root = base / f"{name}-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"
    root.mkdir()
    (root / ".agent").mkdir()
    return root


class Workspace:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative or len(relative) > 220:
            raise ValueError("Use a nonempty relative path up to 220 characters.")
        relative = relative.replace("\\", "/")
        if relative.startswith("/") or PureWindowsPath(relative).drive:
            raise ValueError("Absolute paths and drive paths are forbidden.")
        parts = relative.split("/")
        for part in parts:
            if part in {"", ".", ".."} or part.lower() in {".agent", ".git"}:
                raise ValueError("Traversal, .agent, and .git paths are reserved.")
            if any(ord(c) < 32 or c in '<>:"|?*' for c in part) or part.endswith((" ", ".")):
                raise ValueError("This path contains characters Windows cannot safely use.")
            if part.split(".")[0].upper() in RESERVED:
                raise ValueError("Windows device names cannot be used as files.")
        candidate = self.root.joinpath(*parts)
        for parent in [candidate, *candidate.parents]:
            if parent == self.root:
                break
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise ValueError("Links and junctions are not allowed in generated paths.")
            if parent.is_file() and parent.stat().st_nlink > 1:
                raise ValueError("Hard-linked files cannot be accessed.")
        if not candidate.resolve().is_relative_to(self.root):
            raise ValueError("The path leaves the project directory.")
        return candidate

    def files(self) -> list[str]:
        result = []
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in {".agent", ".git", "__pycache__", "node_modules", ".venv"}
                             and not (Path(directory) / d).is_symlink()
                             and not (hasattr(Path(directory) / d, "is_junction") and (Path(directory) / d).is_junction()))
            for name in sorted(files):
                relative = (Path(directory) / name).relative_to(self.root).as_posix()
                self.path(relative)
                result.append(relative)
                if len(result) > MAX_FILES:
                    raise ValueError(f"Project exceeds the {MAX_FILES} file limit.")
        return result

    def read(self, path: str) -> str:
        p = self.path(path)
        if p.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("File exceeds the 256 KB read limit.")
        return p.read_text(encoding="utf-8-sig")

    def write(self, path: str, content: str) -> dict:
        if not isinstance(content, str) or "\x00" in content:
            raise ValueError("File content must be UTF-8 text without NUL bytes.")
        size = len(content.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise ValueError("File exceeds 256 KB; split it into smaller modules.")
        target = self.path(path)
        paths = self.files()
        if not target.exists() and len(paths) >= MAX_FILES:
            raise ValueError("Project file limit reached.")
        current = sum(self.path(p).stat().st_size for p in paths)
        previous = target.stat().st_size if target.is_file() else 0
        if current - previous + size > MAX_PROJECT_BYTES:
            raise ValueError("Project exceeds the 12 MB limit.")
        atomic_text(target, content)
        return {"written": path, "bytes": size}

    def replace(self, path: str, old: str, new: str) -> dict:
        if not old:
            raise ValueError("The old text must not be empty.")
        original = self.read(path)
        if original.count(old) != 1:
            raise ValueError("old_text must match exactly once; read the file and supply a unique section.")
        return self.write(path, original.replace(old, new, 1))

    def search(self, text: str) -> list[dict]:
        if not text or len(text) > 500:
            raise ValueError("Search for 1–500 characters of literal text.")
        hits = []
        for path in self.files():
            try:
                content = self.read(path)
            except (UnicodeError, ValueError):
                continue
            for number, line in enumerate(content.splitlines(), 1):
                if text in line:
                    hits.append({"path": path, "line": number, "text": line[:300]})
                    if len(hits) >= 60:
                        return hits
        return hits

    def check(self) -> dict:
        files = self.files()
        errors, checked = [], []
        for name in files:
            try:
                if name.endswith(".py"):
                    ast.parse(self.read(name), filename=name)
                    checked.append(name)
                elif name.endswith(".json"):
                    json.loads(self.read(name))
                    checked.append(name)
            except (ValueError, SyntaxError, UnicodeError) as exc:
                errors.append({"path": name, "error": str(exc)[:500]})
        nonempty = [p for p in files if self.path(p).stat().st_size > 0]
        manifest_names = {"requirements.txt", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"}
        requirements = {
            "readme": any(p.lower() == "readme.md" for p in nonempty),
            "dependency_manifest": any(Path(p).name in manifest_names or p.endswith(".csproj") for p in nonempty),
            "source_code": any(Path(p).suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".cs", ".java", ".rs", ".go", ".cpp"}
                               and not self.is_test(p) for p in nonempty),
            "test_cases": any(self.is_test(p) for p in nonempty),
        }
        return {"passed": all(requirements.values()) and not errors,
                "required_outputs": requirements, "syntax_errors": errors,
                "syntax_checked_files": checked, "file_count": len(files),
                "scope": "Checks required files, Python AST syntax and JSON syntax. Does not prove behavior or validate other languages."}

    @staticmethod
    def is_test(path: str) -> bool:
        p = Path(path)
        return (p.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".cs", ".java", ".rs", ".go"}
                and (any(part.lower() in {"test", "tests", "__tests__"} for part in p.parts)
                     or p.name.startswith("test_") or any(s in p.name for s in (".test.", ".spec.", "_test.", "Tests."))))

    def manifest(self) -> list[dict]:
        return [{"path": p, "bytes": self.path(p).stat().st_size,
                 "sha256": hashlib.sha256(self.path(p).read_bytes()).hexdigest()} for p in self.files()]
