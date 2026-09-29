"""Deterministic context selection with a hard serialized UTF-8 byte budget."""
import json
import re
from typing import Any

from .store import Store


def context(store: Store, task: str, project: str, jac_version: str,
            max_bytes: int = 6000) -> dict[str, Any]:
    if not isinstance(max_bytes, int) or not 256 <= max_bytes <= 100_000:
        raise ValueError('max_bytes must be between 256 and 100000')
    packet: dict[str, Any] = {'schema_version': 1, 'trust': 'untrusted_evidence',
                              'items': [], 'truncated': False, 'budget_unit': 'utf8_bytes'}
    terms = set(re.findall(r'\w+', task.lower()))
    records = store.records(project, jac_version)
    scores = {r['id']: len(terms & set(re.findall(r'\w+', r['content'].lower()))) for r in records}
    ranked = sorted((r for r in records if scores[r['id']]), key=lambda r: (-scores[r['id']], r['id']))
    chosen = {r['id'] for r in ranked}
    by_id = {r['id']: r for r in records}
    expanded = []
    for rec in ranked[:8]:
        for neighbor in store.neighbors(rec['id']):
            if neighbor in by_id and neighbor not in chosen:
                expanded.append(by_id[neighbor])
                chosen.add(neighbor)
    for rec in ranked + expanded:
        item = {key: rec[key] for key in ('id', 'kind', 'content', 'source_uri', 'content_hash', 'status', 'jac_version')}
        packet['items'].append(item)
        if len(json.dumps(packet, ensure_ascii=False).encode('utf-8')) > max_bytes:
            packet['items'].pop()
            packet['truncated'] = True
            # Select an attributable window rather than dropping a long guide.
            # Hash/status always describe the complete source, not the excerpt.
            match = next((m for m in re.finditer(r'\w+', rec['content'])
                          if m.group().lower() in terms), None)
            start = max(0, match.start() - 150) if match else 0
            size = min(1800, len(rec['content']) - start)
            while size >= 80:
                item.update(content=rec['content'][start:start + size], is_excerpt=True,
                            excerpt_start=start, excerpt_end=start + size)
                packet['items'].append(item)
                if len(json.dumps(packet, ensure_ascii=False).encode('utf-8')) <= max_bytes:
                    break
                packet['items'].pop()
                size //= 2
    return packet
