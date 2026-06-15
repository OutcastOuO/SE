from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


PROJECT_DIR = Path(__file__).resolve().parent
API_BASE_URL = os.getenv("VMS_API_URL", "http://localhost:8000")
LOG_LINES: deque[str] = deque(maxlen=300)
LOAD_PROCESS: Optional[subprocess.Popen[str]] = None
LOAD_LOCK = threading.Lock()

app = FastAPI(title="VMS Chaos GUI", version="1.0.0")


class LoadStartRequest(BaseModel):
    seconds: int = 180
    delay_seconds: float = 0.3


class ChaosRequest(BaseModel):
    experiment: str
    duration_seconds: int = 30


def _append_log(line: str) -> None:
    LOG_LINES.append(line.rstrip())


def _run_command(command: list[str], timeout: int = 120) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Command not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        _append_log(output)
        raise HTTPException(status_code=504, detail=f"Command timed out after {timeout}s")

    output = (completed.stdout or "") + (completed.stderr or "")
    for line in output.splitlines():
        _append_log(line)
    if completed.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Command failed with exit code {completed.returncode}: {' '.join(command)}",
        )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "output": output,
        "ok": completed.returncode == 0,
    }


def _http_status(path: str) -> dict:
    url = f"{API_BASE_URL}{path}"
    try:
        with urlopen(url, timeout=3) as response:
            body = response.read(300).decode("utf-8", errors="replace")
            return {"ok": True, "status": response.status, "body": body}
    except URLError as exc:
        return {"ok": False, "error": str(exc)}


def _docker_ps() -> str:
    try:
        completed = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except FileNotFoundError:
        return "docker command not found"
    return (completed.stdout or completed.stderr or "").strip()


def _stream_process(process: subprocess.Popen[str], name: str) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        _append_log(f"[{name}] {line}")
    process.wait()
    _append_log(f"[{name}] exited with code {process.returncode}")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/api/status")
def status() -> dict:
    with LOAD_LOCK:
        load_running = LOAD_PROCESS is not None and LOAD_PROCESS.poll() is None
    return {
        "api_base_url": API_BASE_URL,
        "health": _http_status("/health"),
        "chaos_health": _http_status("/api/chaos/health"),
        "load_running": load_running,
        "docker_ps": _docker_ps(),
    }


@app.post("/api/stack/start")
def stack_start() -> dict:
    return _run_command(["docker", "compose", "up", "-d", "--build"], timeout=300)


@app.post("/api/stack/stop")
def stack_stop() -> dict:
    return _run_command(["docker", "compose", "down"], timeout=180)


@app.post("/api/smoke")
def smoke() -> dict:
    return _run_command(["bash", "scripts/smoke-test.sh"], timeout=90)


@app.post("/api/load/start")
def load_start(req: LoadStartRequest) -> dict:
    global LOAD_PROCESS
    if req.seconds < 1 or req.seconds > 3600:
        raise HTTPException(status_code=400, detail="seconds must be between 1 and 3600")
    if req.delay_seconds < 0.05 or req.delay_seconds > 10:
        raise HTTPException(status_code=400, detail="delay_seconds must be between 0.05 and 10")

    with LOAD_LOCK:
        if LOAD_PROCESS is not None and LOAD_PROCESS.poll() is None:
            raise HTTPException(status_code=409, detail="Load test is already running")
        env = os.environ.copy()
        env["BASE_URL"] = API_BASE_URL
        env["DELAY_SECONDS"] = str(req.delay_seconds)
        LOAD_PROCESS = subprocess.Popen(
            ["bash", "scripts/api-load.sh", str(req.seconds)],
            cwd=PROJECT_DIR,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        threading.Thread(target=_stream_process, args=(LOAD_PROCESS, "load"), daemon=True).start()
    _append_log(f"[load] started for {req.seconds}s")
    return {"ok": True, "message": "load test started"}


@app.post("/api/load/stop")
def load_stop() -> dict:
    global LOAD_PROCESS
    with LOAD_LOCK:
        if LOAD_PROCESS is None or LOAD_PROCESS.poll() is not None:
            return {"ok": True, "message": "load test is not running"}
        if os.name == "posix":
            LOAD_PROCESS.send_signal(signal.SIGTERM)
        else:
            LOAD_PROCESS.terminate()
        _append_log("[load] stop requested")
    return {"ok": True, "message": "load test stop requested"}


@app.post("/api/chaos")
def chaos(req: ChaosRequest) -> dict:
    allowed = {"kill", "restart", "stop", "pause", "delay"}
    if req.experiment not in allowed:
        raise HTTPException(status_code=400, detail=f"experiment must be one of {sorted(allowed)}")
    if req.duration_seconds < 1 or req.duration_seconds > 600:
        raise HTTPException(status_code=400, detail="duration_seconds must be between 1 and 600")
    return _run_command(
        ["bash", "scripts/chaos-experiments.sh", req.experiment, str(req.duration_seconds)],
        timeout=max(120, req.duration_seconds + 90),
    )


@app.get("/api/logs")
def logs() -> dict:
    return {"lines": list(LOG_LINES)}


HTML = """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>VMS Chaos GUI</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7f8;
      --ink: #172026;
      --muted: #68737d;
      --line: #d8dee4;
      --panel: #ffffff;
      --accent: #116b68;
      --accent-2: #275d8c;
      --danger: #b42318;
      --warn: #a15c00;
      --ok: #177245;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 750; letter-spacing: 0; }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px;
      display: grid;
      grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
      gap: 18px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    h2 { margin: 0 0 12px; font-size: 15px; }
    .grid { display: grid; gap: 10px; }
    .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    button, input, select {
      height: 36px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      font: inherit;
      padding: 0 10px;
    }
    button {
      cursor: pointer;
      font-weight: 650;
    }
    button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
    button.secondary { background: var(--accent-2); color: #fff; border-color: var(--accent-2); }
    button.danger { background: var(--danger); color: #fff; border-color: var(--danger); }
    button.warn { background: var(--warn); color: #fff; border-color: var(--warn); }
    button:disabled { opacity: .55; cursor: wait; }
    input { width: 96px; }
    select { min-width: 130px; }
    .status {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      min-height: 78px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { margin-top: 6px; font-size: 14px; font-weight: 700; word-break: break-word; }
    .ok { color: var(--ok); }
    .bad { color: var(--danger); }
    pre {
      margin: 0;
      min-height: 360px;
      max-height: 620px;
      overflow: auto;
      white-space: pre-wrap;
      background: #111820;
      color: #dbe8ef;
      border-radius: 8px;
      padding: 14px;
      font-size: 13px;
      line-height: 1.45;
    }
    .links a {
      display: inline-flex;
      align-items: center;
      height: 32px;
      padding: 0 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--accent-2);
      text-decoration: none;
      background: #fff;
      font-weight: 650;
      margin: 0 6px 8px 0;
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; padding: 14px; }
      header { align-items: flex-start; gap: 10px; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <h1>VMS Chaos Testing GUI</h1>
    <div id="apiBase" class="label"></div>
  </header>
  <main>
    <div class="grid">
      <section>
        <h2>Service Status</h2>
        <div class="status">
          <div class="metric"><div class="label">API Health</div><div id="health" class="value">-</div></div>
          <div class="metric"><div class="label">Load Test</div><div id="loadStatus" class="value">-</div></div>
        </div>
      </section>

      <section>
        <h2>Stack</h2>
        <div class="row">
          <button class="primary" onclick="runAction('/api/stack/start')">Start / Rebuild</button>
          <button class="danger" onclick="runAction('/api/stack/stop')">Stop Stack</button>
          <button onclick="runAction('/api/smoke')">Smoke Test</button>
        </div>
      </section>

      <section>
        <h2>API Load</h2>
        <div class="row">
          <label>Seconds <input id="loadSeconds" type="number" min="1" max="3600" value="180"></label>
          <label>Delay <input id="loadDelay" type="number" min="0.05" max="10" step="0.05" value="0.3"></label>
        </div>
        <div class="row" style="margin-top:10px">
          <button class="secondary" onclick="startLoad()">Start Load</button>
          <button class="warn" onclick="runAction('/api/load/stop')">Stop Load</button>
        </div>
      </section>

      <section>
        <h2>Chaos Experiment</h2>
        <div class="row">
          <select id="experiment">
            <option value="kill">kill</option>
            <option value="restart">restart</option>
            <option value="stop">stop</option>
            <option value="pause">pause</option>
            <option value="delay">delay</option>
          </select>
          <label>Seconds <input id="chaosSeconds" type="number" min="1" max="600" value="30"></label>
          <button class="danger" onclick="runChaos()">Run</button>
        </div>
      </section>

      <section>
        <h2>Links</h2>
        <div class="links">
          <a data-port="8000" data-path="/" href="#" target="_blank">API</a>
          <a data-port="9090" data-path="/" href="#" target="_blank">Prometheus</a>
          <a data-port="3000" data-path="/d/vms-chaos/vms-chaos-testing" href="#" target="_blank">Grafana</a>
          <a data-port="9000" data-path="/" href="#" target="_blank">Portainer</a>
        </div>
      </section>
    </div>

    <section>
      <h2>Console</h2>
      <pre id="console"></pre>
    </section>
  </main>

  <script>
    let busy = false;

    function setBusy(next) {
      busy = next;
      document.querySelectorAll('button').forEach(btn => btn.disabled = busy);
    }

    async function postJson(path, body = null) {
      const options = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
      if (body) options.body = JSON.stringify(body);
      const response = await fetch(path, options);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || response.statusText);
      return data;
    }

    async function runAction(path) {
      setBusy(true);
      try {
        await postJson(path);
        await refreshAll();
      } catch (err) {
        appendLocalLog(String(err));
      } finally {
        setBusy(false);
      }
    }

    async function startLoad() {
      setBusy(true);
      try {
        await postJson('/api/load/start', {
          seconds: Number(document.getElementById('loadSeconds').value),
          delay_seconds: Number(document.getElementById('loadDelay').value)
        });
        await refreshAll();
      } catch (err) {
        appendLocalLog(String(err));
      } finally {
        setBusy(false);
      }
    }

    async function runChaos() {
      setBusy(true);
      try {
        await postJson('/api/chaos', {
          experiment: document.getElementById('experiment').value,
          duration_seconds: Number(document.getElementById('chaosSeconds').value)
        });
        await refreshAll();
      } catch (err) {
        appendLocalLog(String(err));
      } finally {
        setBusy(false);
      }
    }

    function appendLocalLog(line) {
      const consoleEl = document.getElementById('console');
      consoleEl.textContent += `\\n[gui] ${line}`;
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    async function refreshStatus() {
      const response = await fetch('/api/status');
      const data = await response.json();
      document.getElementById('apiBase').textContent = data.api_base_url;
      document.getElementById('health').textContent = data.health.ok ? 'ok' : 'down';
      document.getElementById('health').className = `value ${data.health.ok ? 'ok' : 'bad'}`;
      document.getElementById('loadStatus').textContent = data.load_running ? 'running' : 'idle';
      document.getElementById('loadStatus').className = `value ${data.load_running ? 'ok' : ''}`;
    }

    async function refreshLogs() {
      const response = await fetch('/api/logs');
      const data = await response.json();
      const consoleEl = document.getElementById('console');
      consoleEl.textContent = data.lines.join('\\n');
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    async function refreshAll() {
      await Promise.all([refreshStatus(), refreshLogs()]);
    }

    function updateLinks() {
      document.querySelectorAll('a[data-port]').forEach(link => {
        const path = link.dataset.path || '/';
        link.href = `${window.location.protocol}//${window.location.hostname}:${link.dataset.port}${path}`;
      });
    }

    updateLinks();
    refreshAll();
    setInterval(refreshAll, 2500);
  </script>
</body>
</html>
"""
