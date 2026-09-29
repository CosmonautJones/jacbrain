"""Minimal local stdio MCP interface. stdout is reserved for protocol messages."""
import json
from pathlib import Path
from typing import Any, TextIO

from .ingest import ingest_file
from .retrieve import context
from .store import Store
from .validation import validate_record


def schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}


STRING = {'type': 'string'}
TOOLS = [
    {'name': 'context', 'description': 'Return bounded untrusted evidence for a task and exact project/Jac version.',
     'inputSchema': schema({'task': STRING, 'project': STRING, 'jac_version': STRING,
                            'max_bytes': {'type': 'integer', 'minimum': 256, 'maximum': 100000}},
                           ['task', 'project', 'jac_version'])},
    {'name': 'ingest', 'description': 'Ingest one explicitly selected local Markdown/text/Jac file.',
     'inputSchema': schema({'path': STRING, 'project': STRING, 'jac_version': STRING}, ['path', 'project', 'jac_version'])},
    {'name': 'validate', 'description': 'Compile trusted candidate source through real Jac MCP; not runtime testing or sandboxing.',
     'inputSchema': schema({'identity': STRING}, ['identity'])},
]


def dispatch(store: Store, name: str, arguments: dict[str, Any], command: list[str]) -> Any:
    tool = next((item for item in TOOLS if item['name'] == name), None)
    if tool is None:
        raise ValueError('Unknown tool')
    spec = tool['inputSchema']
    if not isinstance(arguments, dict) or set(arguments) - set(spec['properties']):
        raise ValueError('Unexpected tool arguments')
    for key in spec['required']:
        if key not in arguments:
            raise ValueError(f'Missing argument: {key}')
    for key, value in arguments.items():
        if spec['properties'][key]['type'] == 'string' and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f'{key} must be a nonempty string')
    if name == 'context':
        return context(store, **arguments)
    if name == 'ingest':
        return {'ids': ingest_file(store, Path(arguments['path']), arguments['project'], arguments['jac_version'])}
    return validate_record(store, arguments['identity'], command)


def serve(store: Store, source: TextIO, output: TextIO, command: list[str]) -> None:
    for line in source:
        if not line.strip():
            continue
        identity = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError('Request must be an object')
            identity = request.get('id')
            if 'id' not in request:
                continue
            method, params = request.get('method'), request.get('params', {})
            if method == 'initialize':
                result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'jacbrain', 'version': '0.1.0'}}
            elif method == 'ping':
                result = {}
            elif method == 'tools/list':
                result = {'tools': TOOLS}
            elif method == 'tools/call':
                try:
                    value = dispatch(store, params.get('name', ''), params.get('arguments', {}), command)
                    result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}]}
                except (ValueError, RuntimeError, OSError, TypeError) as exc:
                    result = {'isError': True, 'content': [{'type': 'text', 'text': str(exc)}]}
            else:
                output.write(json.dumps({'jsonrpc': '2.0', 'id': identity,
                                         'error': {'code': -32601, 'message': 'Method not found'}}) + '\n')
                output.flush()
                continue
            response = {'jsonrpc': '2.0', 'id': identity, 'result': result}
        except (ValueError, TypeError, AttributeError) as exc:
            response = {'jsonrpc': '2.0', 'id': identity, 'error': {'code': -32600, 'message': str(exc)}}
        output.write(json.dumps(response, ensure_ascii=False) + '\n')
        output.flush()
