"""Section retrieval with lexical ranking, optional graph expansion and byte bounds."""
from collections import Counter
import json
import math
import re
from typing import Any

from .store import Store

GUIDE_PROJECT = '@jac-docs'
STOP = set('a an the to of for from in on with and or is are be it this that how write implement return must using use code jac'.split())


def terms(text: str) -> list[str]:
    """Small deterministic tokenizer; keep source offsets separate from ranking."""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text).lower()
    words = re.findall(r'[^\W_]+', text)
    return [word[:-1] if len(word) > 4 and word.endswith('s') else word
            for word in words if word not in STOP]


def rank(records: list[dict[str, Any]], task: str) -> dict[str, float]:
    query = set(terms(task))
    if not query or not records:
        return {}
    counts = {r['id']: Counter(terms(r['content'])) for r in records}
    average = sum(sum(c.values()) for c in counts.values()) / len(records) or 1
    frequency = Counter(t for c in counts.values() for t in c)
    scores = {}
    for rec in records:
        count = counts[rec['id']]
        length = sum(count.values())
        score = 0.0
        for term in query & count.keys():
            idf = math.log(1 + (len(records) - frequency[term] + .5) / (frequency[term] + .5))
            tf = count[term]
            score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average))
        if score:
            scores[rec['id']] = score
    return scores


def context(store: Store, task: str, project: str, jac_version: str,
            max_bytes: int = 6000, *, include_guides: bool = True,
            expand_graph: bool = True) -> dict[str, Any]:
    if type(max_bytes) is not int or not 256 <= max_bytes <= 100_000:
        raise ValueError('max_bytes must be between 256 and 100000')
    if not isinstance(include_guides, bool) or not isinstance(expand_graph, bool):
        raise ValueError('include_guides and expand_graph must be booleans')
    packet: dict[str, Any] = {'schema_version': 1, 'trust': 'untrusted_evidence',
                              'items': [], 'truncated': False, 'budget_unit': 'utf8_bytes'}
    records = store.records(project, jac_version)
    if include_guides and project != GUIDE_PROJECT:
        records += store.records(GUIDE_PROJECT, jac_version)
    by_id = {r['id']: r for r in records}
    scores = rank(records, task)
    lexical = set(scores)
    seeds = sorted(scores, key=lambda key: (-scores[key], key))[:8]
    if expand_graph:
        # One hop only; graph facts never override version or project isolation.
        for seed in seeds:
            for neighbor in store.neighbors(seed):
                if neighbor in by_id and neighbor not in lexical:
                    scores[neighbor] = max(scores.get(neighbor, 0), scores[seed] * .25)
    ranked = sorted(scores, key=lambda key: (-scores[key], key))
    query = set(terms(task))
    for identity in ranked:
        rec = by_id[identity]
        item = {key: rec[key] for key in ('id', 'kind', 'content', 'source_uri', 'content_hash', 'status', 'jac_version')}
        packet['items'].append(item)
        if len(json.dumps(packet, ensure_ascii=False).encode('utf-8')) > max_bytes:
            packet['items'].pop()
            packet['truncated'] = True
            # Offsets address the complete immutable source. Hash/status describe
            # that source, never a truncated code block's validity.
            matches = [m for m in re.finditer(r'\w+', rec['content']) if set(terms(m.group())) & query]
            center = matches[0].start() if matches else 0
            size = min(1800, len(rec['content']))
            while size >= 80:
                start = max(0, center - min(100, size // 4))
                end = min(len(rec['content']), start + size)
                item.update(content=rec['content'][start:end], is_excerpt=True,
                            excerpt_start=start, excerpt_end=end)
                packet['items'].append(item)
                if len(json.dumps(packet, ensure_ascii=False).encode('utf-8')) <= max_bytes:
                    break
                packet['items'].pop()
                size //= 2
    return packet
