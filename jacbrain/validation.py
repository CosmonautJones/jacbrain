"""Use the installed Jac MCP compiler as evidence, never an LLM's assertion."""
from __future__ import annotations

import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
from typing import Any

from .store import Store


def compiler_version(command: list[str]) -> str:
    try:
        result = subprocess.run([*command, '--version'], capture_output=True, text=True,
                                encoding='utf-8', timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Jac compiler unavailable or version check failed') from exc
    match = re.search(r'\b(\d+\.\d+\.\d+)\b', result.stdout)
    if not match:
        raise RuntimeError('Unrecognized Jac version response')
    return match.group(1)


class JacMCP:
    """Bounded single-client stdio session; no shell interpolation."""

    def __init__(self, command: list[str], timeout: float = 30):
        self.command, self.timeout = command, timeout
        self.messages: queue.Queue[str | None] = queue.Queue()
        self.counter = 0

    def __enter__(self) -> JacMCP:
        self.proc = subprocess.Popen([*self.command, 'mcp'], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, encoding='utf-8', bufsize=1,
                                     start_new_session=(os.name != 'nt'))
        def reader() -> None:
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                self.messages.put(line)
            self.messages.put(None)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        try:
            self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                       'clientInfo': {'name': 'jacbrain', 'version': '0.1.0'}})
            self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def send(self, value: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        completed: queue.Queue[Exception | None] = queue.Queue()
        def write() -> None:
            try:
                self.proc.stdin.write(json.dumps(value) + '\n')
                self.proc.stdin.flush()
                completed.put(None)
            except Exception as exc:
                completed.put(exc)
        self.writer = threading.Thread(target=write, daemon=True)
        self.writer.start()
        try:
            error = completed.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise RuntimeError('Jac MCP write timed out') from exc
        if error is not None:
            raise RuntimeError('Jac MCP input closed') from error

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.counter += 1
        identity = self.counter
        self.send({'jsonrpc': '2.0', 'id': identity, 'method': method, 'params': params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                line = self.messages.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise RuntimeError('Jac MCP timed out') from exc
            if line is None:
                raise RuntimeError('Jac MCP closed before responding')
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError('Jac MCP emitted invalid JSON') from exc
            if not isinstance(response, dict):
                raise RuntimeError('Jac MCP response must be an object')
            if response.get('id') == identity:
                if 'error' in response:
                    raise RuntimeError(f'Jac MCP error: {response["error"]}')
                if not isinstance(response.get('result'), dict):
                    raise RuntimeError('Jac MCP response is missing an object result')
                return response['result']
        raise RuntimeError('Jac MCP timed out')

    def __exit__(self, *_: Any) -> None:
        writing = hasattr(self, 'writer') and self.writer.is_alive()
        if self.proc.stdin and not writing:
            self.proc.stdin.close()
        if writing:
            self.proc.kill()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        if os.name != 'nt':
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.reader.join(timeout=0.1)
        if writing:
            self.writer.join(timeout=0.1)
            if self.proc.stdin and not self.writer.is_alive():
                self.proc.stdin.close()
        # A Windows launcher descendant may inherit stdout. Never block on its
        # stream lock; the daemon reader owns that handle until it observes EOF.
        if self.proc.stdout and not self.reader.is_alive():
            self.proc.stdout.close()


def decode_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get('isError'):
        raise RuntimeError('Jac MCP tool reported an error')
    parts = result.get('content')
    if not isinstance(parts, list):
        raise RuntimeError('Jac MCP content must be an array')
    for part in parts:
        if isinstance(part, dict) and part.get('type') == 'text':
            try:
                payload = json.loads(part['text'])
            except (ValueError, KeyError, TypeError):
                continue
            if isinstance(payload, dict) and isinstance(payload.get('valid'), bool):
                return payload
    raise RuntimeError('Jac MCP did not return a structured validation result')


def validate_record(store: Store, identity: str, command: list[str]) -> dict[str, Any]:
    rec = store.get(identity)
    if rec['kind'] not in {'Pattern', 'Fix', 'Document'}:
        raise ValueError('Validate a Jac source Document, Pattern or Fix')
    version = compiler_version(command)
    if rec['jac_version'] != version:
        raise ValueError(f'Installed Jac {version} does not match evidence {rec["jac_version"]}')
    with JacMCP(command) as client:
        tools = client.request('tools/list', {})
        catalog = tools.get('tools')
        if not isinstance(catalog, list) or not all(isinstance(t, dict) and isinstance(t.get('name'), str) for t in catalog):
            raise RuntimeError('Jac MCP returned a malformed tool catalog')
        if 'validate_jac' not in {t['name'] for t in catalog}:
            raise RuntimeError('Installed Jac MCP does not expose validate_jac')
        result = decode_tool_result(client.request('tools/call', {
            'name': 'validate_jac', 'arguments': {'code': rec['content']}}))
    receipt = store.record_validation(identity, rec['content_hash'], version, result)
    if result.get('errors'):
        diagnostic = store.add(kind='Diagnostic', content=json.dumps(result['errors']),
                               source_uri=f'jac-mcp:receipt/{receipt}', project=rec['project'], jac_version=version)
        store.link(identity, diagnostic, 'produced')
    return {'receipt': receipt, 'status': store.get(identity)['status'], 'scope': 'isolated_snippet', 'result': result}
