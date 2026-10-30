"""Exercise client identity against a loopback-only HTTP policy fixture."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collect_feedback import HttpTransport
from model_simulation import WorkerHttp


USER_AGENT = "Last-Sentence-Evaluation/0.1"


@pytest.fixture(scope="module")
def client_policy_server():
    class PolicyHandler(BaseHTTPRequestHandler):
        def respond(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.headers.get("User-Agent") != USER_AGENT:
                status, data = 403, {"error": "browser_signature_banned", "code": 1010}
            else:
                status, data = 200, {
                    "user_agent": self.headers["User-Agent"],
                    "method": self.command,
                    "authorization": self.headers.get("Authorization"),
                    "content_type": self.headers.get("Content-Type"),
                    "body": json.loads(body) if body else None,
                }
            encoded = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        do_GET = do_POST = respond

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), PolicyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("transport", ["matrix", "feedback"])
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_transports_use_truthful_identity_for_policy_protected_http(
    client_policy_server, monkeypatch, transport, method
):
    # Never route this synthetic fixture traffic through an external proxy.
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    base = client_policy_server
    payload = {"probe": "local-only"} if method == "POST" else None
    default_request = urllib.request.Request(
        base + "/policy",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
    )
    with pytest.raises(urllib.error.HTTPError) as rejected:
        urllib.request.urlopen(default_request, timeout=2)
    with rejected.value as response:
        assert response.code == 403
        assert json.load(response)["error"] == "browser_signature_banned"

    token = "synthetic-loopback-session"
    if transport == "matrix":
        status, data, _ = WorkerHttp(base, token)("/policy", payload, 2)
    else:
        reply = HttpTransport()(method, base + "/policy", body=payload, token=token, timeout=2)
        status, data = reply.status, reply.data
    assert status == 200
    assert data["user_agent"] == USER_AGENT
    assert data["authorization"] == "Bearer " + token
    assert data["method"] == method
    assert data["body"] == payload
    if method == "POST":
        assert data["content_type"] == "application/json"
