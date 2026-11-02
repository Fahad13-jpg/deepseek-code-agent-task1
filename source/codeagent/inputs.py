"""Deterministic Markdown and PlantUML preprocessing; no LLM needed."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

MAX_INPUT_BYTES = 512_000


def read_markdown(path: Path) -> dict:
    path = Path(path)
    if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
        raise ValueError(f"Select a Markdown or text file: {path.name}")
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"{path.name} exceeds the 512 KB input limit.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Save {path.name} with UTF-8 encoding.") from exc
    if not text.strip() or "\x00" in text:
        raise ValueError(f"{path.name} is empty or is not a text file.")
    sections, blocks = [], []
    fence = None
    start = 0
    body = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                blocks.append({"language": language, "line": start, "content": "\n".join(body)})
                fence = None
            else:
                body.append(line)
            continue
        if match:
            fence, language, start, body = match[1], match[2].strip().lower(), number, []
        elif heading := re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line):
            sections.append({"level": len(heading[1]), "title": heading[2], "line": number})
    if fence is not None:
        raise ValueError(f"Unclosed code fence in {path.name}, starting at line {start}.")
    return {"filename": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "text": text, "sections": sections, "code_blocks": blocks,
            "requirement_ids": sorted(set(re.findall(r"\b(?:FR|NFR|ASR)-\d+\b", text)))}


def preprocess(architecture: Path, views: Path) -> dict:
    if Path(architecture).resolve() == Path(views).resolve():
        raise ValueError("Choose two different files for the architecture and UML views.")
    arch, view = read_markdown(architecture), read_markdown(views)
    diagrams, warnings = [], []
    for block in view["code_blocks"]:
        if block["language"] in {"plantuml", "puml", "uml"} or "@startuml" in block["content"]:
            pairs = re.findall(r"@startuml\s*([^\n]*)\n(.*?)@enduml", block["content"], re.S)
            if not pairs:
                warnings.append(f"UML block at line {block['line']} has no complete @startuml / @enduml pair.")
            for name, body in pairs:
                diagrams.append({"name": name.strip() or f"Diagram{len(diagrams)+1}",
                                 "line": block["line"], "source": f"@startuml {name}\n{body}@enduml"})
    if not diagrams:
        warnings.append("No complete PlantUML diagrams were detected; the full views text is still included.")
    if "Requirements document" in arch["text"]:
        warnings.append("The architecture references a separate Requirements document that is not part of these two inputs.")
    if "99.99%" in arch["text"] and "Error budget: 1%" in arch["text"]:
        warnings.append("The stated 99.99% uptime and 1% error budget conflict; record and resolve this assumption in the generated README.")
    if "UserComponent" in arch["text"] and "AdminComponent" in view["text"]:
        warnings.append("The views include AdminComponent, while the architecture overview does not. Account for the admin workflow explicitly.")
    return {"schema_version": 1, "architecture": arch, "views": view,
            "diagrams": diagrams, "warnings": warnings}
