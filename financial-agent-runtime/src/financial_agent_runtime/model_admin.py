"""Tiny local admin page for model-routing.yaml."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from .model_routing import (
    DEFAULT_AGENT_NAMES,
    ModelRoutingConfig,
    explain_model_routes,
    load_model_routing,
    model_routing_path,
    save_model_routing,
    validate_model_routing,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def workspace_root() -> Path:
    return Path.cwd()


class ModelAdminHandler(BaseHTTPRequestHandler):
    server_version = "ModelAdmin/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(INDEX_HTML)
            return
        if path == "/api/config":
            self._send_json(_config_payload())
            return
        if path == "/api/validate":
            self._send_json(_validation_payload())
            return
        self.send_error(404)

    def do_PUT(self) -> None:
        if urlparse(self.path).path != "/api/config":
            self.send_error(404)
            return
        try:
            payload = self._read_json()
            cfg = ModelRoutingConfig(**payload)
            save_model_routing(workspace_root(), cfg)
            self._send_json(_config_payload())
        except (ValueError, ValidationError) as exc:
            self._send_json({"ok": False, "errors": [str(exc)]}, status=400)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/validate":
            self.send_error(404)
            return
        self._send_json(_validation_payload())

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _send_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _config_payload() -> dict:
    root = workspace_root()
    cfg = load_model_routing(root)
    return {
        "path": str(model_routing_path(root)),
        "agent_names": list(DEFAULT_AGENT_NAMES),
        "config": cfg.model_dump(),
        "routes": explain_model_routes(root, DEFAULT_AGENT_NAMES, cfg),
    }


def _validation_payload() -> dict:
    root = workspace_root()
    try:
        cfg = load_model_routing(root)
        errors = validate_model_routing(root, cfg)
        routes = explain_model_routes(root, DEFAULT_AGENT_NAMES, cfg)
    except Exception as exc:
        errors = [str(exc)]
        routes = []
    return {"ok": not errors, "errors": errors, "routes": routes}


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), ModelAdminHandler)
    print(f"Model admin: http://{host}:{port}")
    print(f"Config file: {model_routing_path(workspace_root())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping model admin.")
    finally:
        server.server_close()


def main() -> None:
    run()


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Model Routing</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f5f7f9; color: #172026; }
    header { background: #14213d; color: white; padding: 18px 28px; display: flex; justify-content: space-between; align-items: center; }
    h1 { font-size: 20px; margin: 0; letter-spacing: 0; }
    main { display: grid; grid-template-columns: minmax(320px, 1fr) minmax(360px, 1fr); gap: 18px; padding: 18px; }
    section { background: white; border: 1px solid #d8e0e7; border-radius: 8px; padding: 16px; }
    h2 { margin: 0 0 12px; font-size: 15px; }
    label { display: block; font-size: 12px; color: #52616f; margin-bottom: 4px; }
    input, select { width: 100%; box-sizing: border-box; border: 1px solid #c8d1da; border-radius: 6px; padding: 8px; font-size: 13px; background: white; }
    .row { display: grid; grid-template-columns: 1fr 1fr 180px; gap: 10px; align-items: end; margin-bottom: 10px; }
    .agent-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(160px, 220px) minmax(160px, 220px); gap: 10px; align-items: end; margin-bottom: 10px; }
    .profile { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; border-top: 1px solid #e7edf2; padding-top: 12px; margin-top: 12px; }
    button { border: 0; border-radius: 6px; padding: 8px 12px; background: #1769aa; color: white; font-weight: 600; cursor: pointer; }
    button.secondary { background: #5b6770; }
    button.danger { background: #b42318; }
    .toolbar { display: flex; gap: 10px; }
    .status { white-space: pre-wrap; background: #eef3f7; border-radius: 6px; padding: 10px; font-size: 12px; max-height: 260px; overflow: auto; }
    .key { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
  </style>
</head>
<body>
  <header>
    <h1>Model Routing</h1>
    <div class="toolbar">
      <button id="save">Save</button>
      <button class="secondary" id="validate">Validate</button>
    </div>
  </header>
  <main>
    <section>
      <h2>Agent bindings</h2>
      <div id="agents"></div>
    </section>
    <section>
      <h2>Model profiles</h2>
      <div class="row">
        <div>
          <label>Default model</label>
          <select id="defaultModel"></select>
        </div>
        <div>
          <label>Default multimodal fallback</label>
          <select id="defaultMultimodalModel"></select>
        </div>
        <button id="addProfile" class="secondary">Add profile</button>
      </div>
      <div id="profiles"></div>
      <h2 style="margin-top:18px">Status</h2>
      <div class="status" id="status">Loading...</div>
    </section>
  </main>
  <script>
    let state = null;

    async function loadConfig() {
      const res = await fetch('/api/config');
      state = await res.json();
      render();
      setStatus('Loaded ' + state.path);
    }

    function profileNames() {
      return Object.keys(state.config.models);
    }

    function render() {
      const defaultModel = document.getElementById('defaultModel');
      defaultModel.innerHTML = profileNames().map(name => option(name, state.config.default_model)).join('');
      defaultModel.onchange = () => state.config.default_model = defaultModel.value;
      const defaultMultimodalModel = document.getElementById('defaultMultimodalModel');
      defaultMultimodalModel.innerHTML = emptyOption('None') + profileNames().map(name => option(name, state.config.default_multimodal_model || '')).join('');
      defaultMultimodalModel.onchange = () => state.config.default_multimodal_model = defaultMultimodalModel.value || null;

      const agents = document.getElementById('agents');
      agents.innerHTML = state.agent_names.map(agent => {
        const route = agentRoute(agent);
        const selected = route.model || state.config.default_model;
        const fallback = route.multimodal_fallback_model || '';
        return `<div class="agent-row">
          <div><label class="key">${agent}</label></div>
          <div><label>Main</label><select data-agent="${agent}" data-agent-field="model">${profileNames().map(name => option(name, selected)).join('')}</select></div>
          <div><label>Multimodal fallback</label><select data-agent="${agent}" data-agent-field="multimodal_fallback_model">${emptyOption('Use default')}${profileNames().map(name => option(name, fallback)).join('')}</select></div>
        </div>`;
      }).join('');
      agents.querySelectorAll('select[data-agent]').forEach(select => {
        select.onchange = () => {
          const agent = select.dataset.agent;
          const route = agentRoute(agent);
          route[select.dataset.agentField] = select.value || null;
          state.config.agent_models[agent] = compactRoute(route);
        };
      });

      const profiles = document.getElementById('profiles');
      profiles.innerHTML = profileNames().map(name => profileEditor(name, state.config.models[name])).join('');
      profiles.querySelectorAll('[data-profile-field]').forEach(input => {
        input.oninput = () => {
          const profile = state.config.models[input.dataset.profile];
          const field = input.dataset.profileField;
          if (field === 'max_tokens') {
            profile[field] = Number(input.value || 0);
          } else if (field === 'reasoning_effort') {
            profile[field] = input.value || null;
          } else {
            profile[field] = input.value;
          }
        };
      });
      profiles.querySelectorAll('button[data-delete-profile]').forEach(button => {
        button.onclick = () => {
          const name = button.dataset.deleteProfile;
          delete state.config.models[name];
          for (const agent of Object.keys(state.config.agent_models)) {
            const route = agentRoute(agent);
            if (route.model === name) route.model = state.config.default_model;
            if (route.multimodal_fallback_model === name) route.multimodal_fallback_model = null;
            state.config.agent_models[agent] = compactRoute(route);
          }
          if (state.config.default_model === name) state.config.default_model = profileNames()[0] || '';
          if (state.config.default_multimodal_model === name) state.config.default_multimodal_model = null;
          render();
        };
      });
    }

    function agentRoute(agent) {
      const raw = state.config.agent_models[agent];
      if (!raw) return {};
      if (typeof raw === 'string') return {model: raw};
      return {...raw};
    }

    function compactRoute(route) {
      if (!route.multimodal_fallback_model) delete route.multimodal_fallback_model;
      if (!route.model) delete route.model;
      return route;
    }

    function emptyOption(label) {
      return `<option value="">${escapeHtml(label)}</option>`;
    }

    function option(name, selected) {
      return `<option value="${escapeHtml(name)}" ${name === selected ? 'selected' : ''}>${escapeHtml(name)}</option>`;
    }

    function profileEditor(name, profile) {
      return `<div class="profile">
        <div><label>Profile key</label><input value="${escapeHtml(name)}" disabled></div>
        <div><label>Model</label><input data-profile="${escapeHtml(name)}" data-profile-field="model" value="${escapeHtml(profile.model)}"></div>
        <div><label>Base URL</label><input data-profile="${escapeHtml(name)}" data-profile-field="base_url" value="${escapeHtml(profile.base_url)}"></div>
        <div><label>API key env</label><input data-profile="${escapeHtml(name)}" data-profile-field="api_key_env" value="${escapeHtml(profile.api_key_env || '')}"></div>
        <div><label>Max tokens</label><input type="number" data-profile="${escapeHtml(name)}" data-profile-field="max_tokens" value="${profile.max_tokens}"></div>
        <div><label>Thinking</label><select data-profile="${escapeHtml(name)}" data-profile-field="thinking">${['auto','enabled','disabled'].map(v => option(v, profile.thinking)).join('')}</select></div>
        <div><label>Reasoning effort</label><select data-profile="${escapeHtml(name)}" data-profile-field="reasoning_effort">${emptyOption('Provider default')}${['low','medium','high','max','xhigh'].map(v => option(v, profile.reasoning_effort || '')).join('')}</select></div>
        <button class="danger" data-delete-profile="${escapeHtml(name)}">Delete</button>
      </div>`;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }

    function setStatus(value) {
      document.getElementById('status').textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    }

    document.getElementById('addProfile').onclick = () => {
      const name = prompt('Profile key');
      if (!name) return;
      state.config.models[name] = {
        model: '',
        base_url: '',
        api_key_env: '',
        max_tokens: 16000,
        thinking: 'auto',
        reasoning_effort: null
      };
      render();
    };

    document.getElementById('save').onclick = async () => {
      const res = await fetch('/api/config', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(state.config)});
      const payload = await res.json();
      if (!res.ok) { setStatus(payload); return; }
      state = payload;
      render();
      setStatus('Saved ' + state.path);
    };

    document.getElementById('validate').onclick = async () => {
      const res = await fetch('/api/validate', {method: 'POST'});
      setStatus(await res.json());
    };

    loadConfig().catch(err => setStatus(String(err)));
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
