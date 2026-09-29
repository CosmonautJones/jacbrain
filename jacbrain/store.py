"""Transactional evidence graph. Source content is immutable and addressed by hash."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KINDS = {'Concept', 'Document', 'Symbol', 'Diagnostic', 'Fix', 'Pattern', 'Task', 'Validation'}
RELATIONS = {'documents', 'depends_on', 'fixes', 'validates', 'produced', 'used_in'}


def digest(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


class Store:
    """One local SQLite store; each operation commits atomically."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys = ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL,
                source_uri TEXT NOT NULL, content_hash TEXT NOT NULL,
                project TEXT NOT NULL, jac_version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'candidate', created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS scope ON records(project, jac_version);
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT REFERENCES records(id), target TEXT REFERENCES records(id),
                relation TEXT NOT NULL, PRIMARY KEY(source, target, relation)
            );
        ''')

    def close(self) -> None:
        self.db.close()

    def add(self, *, kind: str, content: str, source_uri: str,
            project: str, jac_version: str) -> str:
        if kind not in KINDS or not all((content.strip(), source_uri, project, jac_version)):
            raise ValueError('A valid kind, nonempty content, provenance, project and version are required')
        if len(content.encode('utf-8')) > 100_000:
            raise ValueError('Record exceeds 100000 UTF-8 bytes; split the source')
        content_hash = digest(content)
        identity = digest(json.dumps([kind, content_hash, source_uri, project, jac_version]))
        with self.db:
            self.db.execute("UPDATE records SET status='superseded' WHERE kind=? AND source_uri=? AND project=? AND jac_version=? AND id<>?",
                            (kind, source_uri, project, jac_version, identity))
            self.db.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?,?,?,?,?,?)',
                            (identity, kind, content, source_uri, content_hash, project,
                             jac_version, 'candidate', datetime.now(timezone.utc).isoformat()))
            self.db.execute("UPDATE records SET status='candidate' WHERE id=? AND status='superseded'", (identity,))
        return identity

    def get(self, identity: str) -> dict[str, Any]:
        row = self.db.execute('SELECT * FROM records WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError('Unknown evidence ID')
        return dict(row)

    def records(self, project: str, jac_version: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM records WHERE project=? AND jac_version=? AND status<>'superseded' ORDER BY id",
            (project, jac_version))]

    def supersede_symbols(self, source_uri: str, project: str, jac_version: str) -> None:
        prefix = source_uri + '#L'
        with self.db:
            self.db.execute("UPDATE records SET status='superseded' WHERE kind='Symbol' AND substr(source_uri,1,?)=? AND project=? AND jac_version=?",
                            (len(prefix), prefix, project, jac_version))

    def link(self, source: str, target: str, relation: str) -> None:
        if relation not in RELATIONS:
            raise ValueError('Unknown relation')
        left, right = self.get(source), self.get(target)
        if (left['project'], left['jac_version']) != (right['project'], right['jac_version']):
            raise ValueError('Cross-project or cross-version relations are not supported')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?)', (source, target, relation))

    def neighbors(self, identity: str) -> list[str]:
        return [row[0] for row in self.db.execute(
            'SELECT target FROM edges WHERE source=? UNION SELECT source FROM edges WHERE target=?',
            (identity, identity))]

    def record_validation(self, identity: str, content_hash: str, compiler_version: str,
                          result: dict[str, Any]) -> str:
        """Internal trusted-adapter API, never exposed as a caller-supplied receipt tool."""
        rec = self.get(identity)
        if rec['status'] == 'superseded':
            raise ValueError('Cannot promote superseded evidence; re-ingest the current source')
        if rec['content_hash'] != content_hash or rec['jac_version'] != compiler_version:
            raise ValueError('Receipt source hash or compiler version does not match')
        passed = result.get('valid') is True and not result.get('errors')
        payload = json.dumps({'candidate': identity, 'content_hash': content_hash,
                              'compiler_version': compiler_version, 'tool': 'validate_jac',
                              'scope': 'isolated_snippet', 'result': result}, sort_keys=True)
        # Keep record + edge + promotion in one transaction (add/link commit independently).
        receipt = digest(json.dumps(['Validation', digest(payload), 'jac-mcp:validate_jac',
                                     rec['project'], compiler_version]))
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?,?,?,?,?,?)',
                            (receipt, 'Validation', payload, 'jac-mcp:validate_jac', digest(payload),
                             rec['project'], compiler_version, 'candidate',
                             datetime.now(timezone.utc).isoformat()))
            self.db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?)', (receipt, identity, 'validates'))
            self.db.execute('UPDATE records SET status=? WHERE id=?',
                            ('compiler_validated' if passed else 'candidate', identity))
        return receipt
