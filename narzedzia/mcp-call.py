import json
import os
import subprocess
import sys
import tempfile
import uuid

HOST = "rpi"
URL = "http://localhost:3000/mcp"


def _ssh(cmd: str) -> str:
    r = subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ssh failed: {r.stderr}")
    return r.stdout


def _scp_up(local: str, remote: str) -> None:
    subprocess.run(["scp", local, f"{HOST}:{remote}"], check=True)


def call(tool: str, args: dict) -> dict:
    tmp = os.path.join(tempfile.gettempdir(), "opencode", "mcp")
    os.makedirs(tmp, exist_ok=True)
    sid = str(uuid.uuid4())

    def payload(name, obj):
        p = os.path.join(tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return p

    init = payload("mcp-init.json", {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "claims-mcp-helper", "version": "1.0"}}})
    notif = payload("mcp-notif.json", {"jsonrpc": "2.0", "method": "notifications/initialized"})
    req = payload("mcp-call.json", {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": tool, "arguments": args}})
    out = os.path.join(tmp, "mcp-out.txt")

    accept = "Accept: application/json, text/event-stream"
    auth = "Authorization: Bearer " + os.environ["N8N_MCP_AUTH_TOKEN"]
    _scp_up(init, "/tmp/mcp-init.json")
    _scp_up(notif, "/tmp/mcp-notif.json")
    _scp_up(req, "/tmp/mcp-call.json")

    hdr = "/tmp/mcp-hdr.txt"

    def curl(*extra: str) -> str:
        parts = ["curl", "-s", "-X", "POST", URL,
                 "-H", "'Content-Type: application/json'",
                 "-H", f"'{accept}'", "-H", f"'{auth}'"] + list(extra)
        return " ".join(parts)

    _ssh(curl(f"-D {hdr}", "--data-binary @/tmp/mcp-init.json"))
    sess = ""
    for line in _ssh(f"cat {hdr}").splitlines():
        if line.lower().startswith("mcp-session-id:"):
            sess = line.split(":", 1)[1].strip()
    if not sess:
        raise RuntimeError("no session id from initialize")
    h = f"-H 'Mcp-Session-Id: {sess}'"
    _ssh(curl(h, "--data-binary @/tmp/mcp-notif.json", ">/dev/null"))
    _ssh(curl(h, "--data-binary @/tmp/mcp-call.json", "-o /tmp/mcp-out.txt"))
    subprocess.run(["scp", f"{HOST}:/tmp/mcp-out.txt", out], check=True)

    raw = open(out, encoding="utf-8").read()
    for line in raw.splitlines():
        if line.startswith("data: "):
            resp = json.loads(line[6:])
            content = resp.get("result", {}).get("content", [])
            text = "\n".join(c.get("text", "") for c in content)
            if resp.get("result", {}).get("isError"):
                raise RuntimeError(text)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    raise RuntimeError(f"no SSE data in response: {raw[:400]}")


if __name__ == "__main__":
    tool = sys.argv[1]
    if len(sys.argv) > 2:
        src = sys.argv[2]
        raw = open(src, encoding="utf-8-sig").read() if os.path.exists(src) else src
        args = json.loads(raw)
    else:
        args = json.load(sys.stdin)
    result = call(tool, args)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
