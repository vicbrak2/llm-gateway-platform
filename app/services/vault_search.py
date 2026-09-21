from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

VAULT_DIR = Path(__file__).resolve().parent.parent / 'data' / 'vault'
WORD_RE = re.compile(r'[a-záéíóúñü0-9]+', re.IGNORECASE)

# Common Spanish/English stopwords that would otherwise dominate the overlap
# score without carrying any topical signal.
STOPWORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al',
    'y', 'o', 'que', 'en', 'es', 'con', 'por', 'para', 'se', 'su', 'sus',
    'como', 'a', 'no', 'the', 'a', 'an', 'of', 'and', 'or', 'to', 'in', 'is',
    'for', 'on', 'do', 'i', 'you', 'my', 'are', 'have',
}


@dataclass(frozen=True)
class VaultDoc:
    path: str  # relative path, e.g. "general/Arquitectura.md"
    title: str
    content: str


def _tokenize(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 2]


def _title_from_content(path: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip()
    return path.stem


@lru_cache
def _load_docs() -> tuple[VaultDoc, ...]:
    if not VAULT_DIR.is_dir():
        return ()
    docs = []
    for path in sorted(VAULT_DIR.rglob('*.md')):
        content = path.read_text(encoding='utf-8', errors='ignore')
        rel_path = str(path.relative_to(VAULT_DIR))
        docs.append(VaultDoc(path=rel_path, title=_title_from_content(path, content), content=content))
    return tuple(docs)


def search(query: str, top_k: int = 3, max_chars_per_doc: int = 1500) -> list[VaultDoc]:
    """Very small keyword-overlap search over the bundled vault markdown files.

    No embeddings/vector store: the vault is a few dozen files, so a linear
    bag-of-words scoring pass is fast enough and needs no extra infra.
    """
    docs = _load_docs()
    if not docs:
        return []
    query_terms = set(_tokenize(query))
    if not query_terms:
        return []

    scored: list[tuple[int, VaultDoc]] = []
    for doc in docs:
        doc_terms = _tokenize(doc.title) * 3 + _tokenize(doc.content)  # title matches count more
        if not doc_terms:
            continue
        score = sum(1 for term in doc_terms if term in query_terms)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [doc for _, doc in scored[:top_k]]
    return [
        VaultDoc(path=doc.path, title=doc.title, content=doc.content[:max_chars_per_doc])
        for doc in top
    ]


def clear_cache() -> None:
    """Test helper: drop the cached doc list so a test can point VAULT_DIR elsewhere."""
    _load_docs.cache_clear()
