"""Explicit local ingestion. Lexical symbols are candidates, never semantic truth."""
from pathlib import Path
import re

from .store import Store

DECLARATION = re.compile(r'^\s*(node|edge|walker|obj|def)\s+([A-Za-z_]\w*)', re.MULTILINE)


def ingest_file(store: Store, path: Path, project: str, jac_version: str) -> list[str]:
    path = path.resolve()
    if not path.is_file() or path.suffix.lower() not in {'.md', '.txt', '.jac'}:
        raise ValueError('Select an explicit .md, .txt or .jac file')
    if path.stat().st_size > 100_000:
        raise ValueError('File exceeds 100000 bytes; split it explicitly')
    content = path.read_text(encoding='utf-8')
    root = store.add(kind='Document', content=content, source_uri=path.as_uri(),
                     project=project, jac_version=jac_version)
    ids = [root]
    if path.suffix.lower() == '.jac':
        store.supersede_symbols(path.as_uri(), project, jac_version)
        for match in DECLARATION.finditer(content):
            line = content[:match.start()].count('\n') + 1
            symbol = store.add(kind='Symbol', content=f'{match.group(1)} {match.group(2)} (lexical candidate)',
                               source_uri=f'{path.as_uri()}#L{line}', project=project, jac_version=jac_version)
            store.link(root, symbol, 'documents')
            ids.append(symbol)
    return ids
