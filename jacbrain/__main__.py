"""Run with python -m jacbrain; no hosted service or model account required."""
import argparse
import json
import os
from pathlib import Path
import sys

from .ingest import ingest_file
from .retrieve import context
from .server import serve
from .store import KINDS, Store
from .validation import validate_record


def main() -> int:
    parser = argparse.ArgumentParser(description='Versioned Jac engineering memory')
    parser.add_argument('--db', default='.jacbrain/brain.sqlite3')
    parser.add_argument('--jac-command', default=os.environ.get('JACBRAIN_JAC_COMMAND', '["jac"]'),
                        help='JSON argv array, e.g. ["wsl","-d","Ubuntu","--","jac"]')
    commands = parser.add_subparsers(dest='action', required=True)
    for name in ('ingest', 'remember', 'context'):
        sub = commands.add_parser(name)
        sub.add_argument('--project', required=True)
        sub.add_argument('--jac-version', default='0.37.23')
        if name == 'context':
            sub.add_argument('task')
            sub.add_argument('--max-bytes', type=int, default=6000)
        else:
            sub.add_argument('path', type=Path)
            if name == 'remember':
                sub.add_argument('--kind', choices=sorted(KINDS), required=True)
    check = commands.add_parser('validate')
    check.add_argument('identity')
    link = commands.add_parser('link')
    link.add_argument('source')
    link.add_argument('relation')
    link.add_argument('target')
    commands.add_parser('mcp')
    args = parser.parse_args()
    store = None
    try:
        command = json.loads(args.jac_command)
        if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
            raise ValueError('--jac-command must be a nonempty JSON string array')
        path = Path(args.db)
        path.parent.mkdir(parents=True, exist_ok=True)
        store = Store(path)
        if args.action == 'mcp':
            serve(store, sys.stdin, sys.stdout, command)
            return 0
        if args.action == 'ingest':
            result = {'ids': ingest_file(store, args.path, args.project, args.jac_version)}
        elif args.action == 'remember':
            if not args.path.is_file() or args.path.stat().st_size > 100_000:
                raise ValueError('Select a file of at most 100000 bytes')
            result = {'id': store.add(kind=args.kind, content=args.path.read_text(encoding='utf-8'),
                                     source_uri=args.path.resolve().as_uri(), project=args.project, jac_version=args.jac_version)}
        elif args.action == 'context':
            result = context(store, args.task, args.project, args.jac_version, args.max_bytes)
        elif args.action == 'link':
            store.link(args.source, args.target, args.relation)
            result = {'linked': True}
        else:
            result = validate_record(store, args.identity, command)
        print(json.dumps(result, ensure_ascii=False, indent=None if args.action == 'context' else 2))
        if args.action == 'validate' and result['status'] != 'compiler_validated':
            return 1
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'jacbrain: {exc}', file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()


if __name__ == '__main__':
    raise SystemExit(main())
