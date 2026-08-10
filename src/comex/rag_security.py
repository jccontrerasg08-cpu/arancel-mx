"""Static safety checks for local RAG documents."""

from __future__ import annotations

import re
from pathlib import Path

from .legal_corpus import SUPPORTED_SUFFIXES, corpus_dir


PATTERNS = [
    ("prompt_injection", "HIGH", re.compile(r"\b(ignore|disregard|forget)\b.{0,80}\b(previous|system|developer|instructions?)\b", re.I)),
    ("prompt_injection", "HIGH", re.compile(r"\b(ignora|olvida)\b.{0,80}\b(instrucciones|sistema|desarrollador)\b", re.I)),
    ("prompt_leakage", "HIGH", re.compile(r"\b(system prompt|developer message|reveal prompt|muestra el prompt)\b", re.I)),
    ("secret_harvest", "HIGH", re.compile(r"\b(api[_ -]?key|token|password|secret|\.env|ssh key|private key)\b", re.I)),
    ("exfiltration", "HIGH", re.compile(r"\b(send|post|upload|exfiltrate|transmit|curl)\b.{0,120}\b(http|webhook|telegram|discord|pastebin)\b", re.I)),
    ("code_execution", "MEDIUM", re.compile(r"\b(eval|exec|subprocess|os\.system|powershell|cmd\.exe|bash)\b", re.I)),
    ("hidden_instruction", "MEDIUM", re.compile(r"<!--|-->|\\u200b|\\u200c|\\u200d|base64|atob\(", re.I)),
]


def scan_rag_corpus(root: Path | None = None) -> dict:
    root = root or corpus_dir()
    findings = []
    for path in _files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(root))
        for kind, severity, pattern in PATTERNS:
            for match in pattern.finditer(text):
                findings.append({
                    "source": rel,
                    "kind": kind,
                    "severity": severity,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "match": re.sub(r"\s+", " ", match.group(0)).strip()[:160],
                })
    return {
        "path": str(root),
        "files": len(_files(root)),
        "findings": findings,
        "risk": _risk(findings),
    }


def _files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and path.name.lower() != "readme.md"
        and not path.name.startswith(".")
    )


def _risk(findings: list[dict]) -> str:
    if any(item["severity"] == "HIGH" for item in findings):
        return "high"
    if findings:
        return "medium"
    return "low"
