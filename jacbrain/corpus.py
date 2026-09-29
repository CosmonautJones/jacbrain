"""Atomic, version-pinned imports of the installed compiler's bundled guides."""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any
from urllib.parse import quote

from .store import Store, digest
from .validation import JacMCP, compiler_version

PROJECT = '@jac-docs'
MAX_GUIDES = 100
MAX_DOCUMENT_BYTES = 1_000_000
CHUNK_BYTES = 90_000
GUIDE_URI = re.compile(r'^jac://guide/[A-Za-z0-9][A-Za-z0-9_-]*$')
SCHEMA = '''CREATE TABLE IF NOT EXISTS guide_chunks (
    record_id TEXT PRIMARY KEY REFERENCES records(id), doc_uri TEXT NOT NULL,
    title TEXT NOT NULL, section TEXT NOT NULL, ordinal INTEGER NOT NULL,
    document_hash TEXT NOT NULL
)'''


def _check_version(payload: dict[str, Any], version: str) -> None:
    for key in ('jac_version', 'compiler_version'):
        if key in payload and payload[key] != version:
            raise ValueError('Guide resource compiler version mismatch')


def _discover(client: JacMCP, version: str) -> dict[str, str]:
    catalog: dict[str, str] = {}
    cursor: str | None = None
    cursors: set[str] = set()
    for _ in range(100):
        response = client.request('resources/list', {'cursor': cursor} if cursor else {})
        _check_version(response, version)
        resources = response.get('resources')
        if not isinstance(resources, list):
            raise ValueError('Malformed Jac resource catalog')
        for resource in resources:
            if not isinstance(resource, dict) or not isinstance(resource.get('uri'), str):
                raise ValueError('Malformed Jac resource identity')
            uri = resource['uri']
            if not uri.startswith('jac://guide/'):
                continue
            if not GUIDE_URI.fullmatch(uri) or uri in catalog:
                raise ValueError('Malformed or duplicate guide URI')
            _check_version(resource, version)
            name = resource.get('name', uri.rsplit('/', 1)[-1])
            if not isinstance(name, str) or not name.strip():
                raise ValueError('Malformed guide title')
            catalog[uri] = name
            if len(catalog) > MAX_GUIDES:
                raise ValueError('Guide catalog exceeds 100 guides')
        cursor = response.get('nextCursor')
        if cursor is None:
            break
        if not isinstance(cursor, str) or not cursor or cursor in cursors:
            raise ValueError('Malformed or repeated resource cursor')
        cursors.add(cursor)
    else:
        raise ValueError('Resource pagination exceeded its bound')
    if not catalog:
        raise ValueError('Installed compiler exposes no guide resources')
    return catalog


def _read(client: JacMCP, uri: str, version: str) -> str:
    response = client.request('resources/read', {'uri': uri})
    _check_version(response, version)
    contents = response.get('contents')
    if not isinstance(contents, list) or len(contents) != 1:
        raise ValueError('Guide read must return exactly one text resource')
    resource = contents[0]
    if not isinstance(resource, dict) or resource.get('uri') != uri:
        raise ValueError('Guide read returned a different resource identity')
    _check_version(resource, version)
    text = resource.get('text')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Guide resource is empty or not text')
    if len(text.encode('utf-8')) > MAX_DOCUMENT_BYTES:
        raise ValueError('Guide resource exceeds 1 MB')
    return text


def _sections(text: str) -> list[tuple[str, str]]:
    """Split at ATX headings outside fences; preserve every original source byte."""
    result: list[tuple[str, str]] = []
    heading = 'Introduction'
    lines: list[str] = []
    fence = ''
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            token = marker[1]
            if not fence:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not marker[2].strip():
                fence = ''
            lines.append(line)
            continue
        match = re.match(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$', line) if not fence else None
        if match:
            if lines:
                result.append((heading, ''.join(lines)))
            heading, lines = match[1], [line]
        else:
            lines.append(line)
    if lines:
        result.append((heading, ''.join(lines)))
    return result


def _parts(section: str) -> list[str]:
    """Prefer cuts outside code fences; oversized single fences use lossless cuts."""
    if len(section.encode('utf-8')) <= CHUNK_BYTES:
        return [section]
    result: list[str] = []
    pending = ''
    fence = ''
    safe_cut = 0
    for line in section.splitlines(keepends=True):
        pending += line
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            token = marker[1]
            if not fence:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not marker[2].strip():
                fence = ''
        while len(pending.encode('utf-8')) > CHUNK_BYTES:
            cut = safe_cut or len(pending.encode('utf-8')[:CHUNK_BYTES].decode('utf-8', errors='ignore'))
            result.append(pending[:cut])
            pending = pending[cut:]
            safe_cut = 0
        if not fence:
            safe_cut = len(pending)
    if pending:
        result.append(pending)
    return result


def _stage_document(stage: Store, uri: str, title: str, text: str, version: str) -> None:
    counts: Counter[str] = Counter()
    used_keys: set[str] = set()
    ordinal = 0
    for section, body in _sections(text):
        slug = re.sub(r'[^\w-]+', '-', section.lower()).strip('-') or 'section'
        counts[slug] += 1
        key = slug if counts[slug] == 1 else f'{slug}-{counts[slug]}'
        while key in used_keys:
            counts[slug] += 1
            key = f'{slug}-{counts[slug]}'
        used_keys.add(key)
        for part, content in enumerate(_parts(body), 1):
            if not content.strip():
                continue
            source_uri = uri + '#' + quote(key, safe='-') + f'/{part}'
            identity = stage.add(kind='Document' if ordinal == 0 else 'Concept', content=content,
                                 source_uri=source_uri, project=PROJECT, jac_version=version)
            stage.db.execute('INSERT INTO guide_chunks VALUES (?,?,?,?,?,?)',
                             (identity, uri, title, section, ordinal, digest(text)))
            stage.db.commit()
            ordinal += 1


def _references(text: str) -> set[str]:
    explicit = set(re.findall(r'jac://guide/[A-Za-z0-9][A-Za-z0-9_-]*', text))
    explicit.update('jac://guide/' + name for name in re.findall(r'`(jac-[a-z0-9][a-z0-9-]*)`', text))
    return explicit


def sync_guides(store: Store, command: list[str], *, uris: list[str] | None = None) -> dict[str, Any]:
    """Fetch, stage and atomically replace the selected versioned guide snapshots."""
    if uris is not None and (not isinstance(uris, list) or not all(isinstance(uri, str) for uri in uris)):
        raise ValueError('Guide URIs must be a list of strings')
    version = compiler_version(command)
    with JacMCP(command) as client:
        catalog = _discover(client, version)
        selected = sorted(catalog if uris is None else uris)
        if not selected or len(selected) > MAX_GUIDES or len(set(selected)) != len(selected):
            raise ValueError('Select 1..100 distinct guide URIs')
        if any(uri not in catalog for uri in selected):
            raise ValueError('Selected guide is absent from installed compiler catalog')
        documents = [(uri, catalog[uri], _read(client, uri, version)) for uri in selected]
    if compiler_version(command) != version:
        raise ValueError('Compiler version changed during guide import')
    stage = Store(':memory:')
    try:
        stage.db.execute(SCHEMA)
        for uri, title, text in documents:
            _stage_document(stage, uri, title, text, version)
        selected_ids = {row[0] for row in stage.db.execute('SELECT id FROM records')}
        has_metadata = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='guide_chunks'").fetchone()
        existing_metadata = [] if not has_metadata else list(store.db.execute('''
            SELECT g.* FROM guide_chunks g JOIN records r ON r.id=g.record_id
            WHERE r.project=? AND r.jac_version=? AND r.status<>'superseded'
        ''', (PROJECT, version)))
        for meta in existing_metadata:
            if uris is not None and meta['doc_uri'] not in selected:
                rec = store.db.execute('SELECT * FROM records WHERE id=?', (meta['record_id'],)).fetchone()
                stage.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?)', tuple(rec))
                stage.db.execute('INSERT INTO guide_chunks VALUES (?,?,?,?,?,?)', tuple(meta))
        stage.db.commit()
        metadata = list(stage.db.execute('SELECT * FROM guide_chunks ORDER BY doc_uri, ordinal'))
        intros = {row['doc_uri']: row['record_id'] for row in metadata if row['ordinal'] == 0}
        for meta in metadata:
            identity = meta['record_id']
            if identity != intros[meta['doc_uri']]:
                stage.link(identity, intros[meta['doc_uri']], 'documents')
            for target_uri in sorted(_references(stage.get(identity)['content'])):
                if target_uri in intros and intros[target_uri] != identity:
                    stage.link(identity, intros[target_uri], 'depends_on')
        snapshot = sorted({(row['doc_uri'], row['document_hash']) for row in metadata})
        snapshot_hash = digest(json.dumps({'jac_version': version, 'documents': snapshot}, sort_keys=True, separators=(',', ':')))
        if store.db.in_transaction:
            raise RuntimeError('Cannot import guides inside another database transaction')
        with store.db:
            store.db.execute('BEGIN IMMEDIATE')
            store.db.execute(SCHEMA)
            for meta in existing_metadata:
                if (uris is None or meta['doc_uri'] in selected) and meta['record_id'] not in selected_ids:
                    store.db.execute("UPDATE records SET status='superseded' WHERE id=?", (meta['record_id'],))
            for rec in stage.db.execute('SELECT * FROM records'):
                store.db.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?,?,?,?,?,?)', tuple(rec))
                store.db.execute("UPDATE records SET status='candidate' WHERE id=? AND status='superseded'", (rec['id'],))
            for meta in metadata:
                store.db.execute('INSERT OR REPLACE INTO guide_chunks VALUES (?,?,?,?,?,?)', tuple(meta))
            # Corpus relationships are owned by this importer. Rebuild against all
            # active guides so partial refreshes repair references into changed docs.
            store.db.execute('''DELETE FROM edges WHERE relation IN ('documents','depends_on') AND source IN (
                SELECT g.record_id FROM guide_chunks g JOIN records r ON r.id=g.record_id
                WHERE r.project=? AND r.jac_version=?)''', (PROJECT, version))
            store.db.executemany('INSERT OR IGNORE INTO edges VALUES (?,?,?)',
                                 [tuple(row) for row in stage.db.execute('SELECT * FROM edges')])
        return {'jac_version': version, 'documents': len(documents), 'chunks': len(selected_ids),
                'edges': stage.db.execute('SELECT count(*) FROM edges').fetchone()[0],
                'total_documents': len(snapshot), 'total_chunks': len(metadata), 'snapshot_hash': snapshot_hash}
    finally:
        stage.close()
