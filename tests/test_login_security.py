import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


ROOT = Path(__file__).resolve().parents[1]
LOGIN_CHECK = ROOT / "lifecycle" / "login-check.sh"


class LoginFixtureHandler(BaseHTTPRequestHandler):
    authenticated_marker = True
    post_count = 0
    logout_count = 0
    post_redirect_url = None
    suppress_session_cookie = False

    def log_message(self, format, *args):
        del format, args
        return

    def do_GET(self):
        if self.path == "/users/login":
            body = (
                '<form method="post">'
                '<input type="hidden" name="csrf" value="fixture">'
                '<input type="email" name="data[User][email]">'
                '<input type="password" name="data[User][password]">'
                '</form>'
            )
        elif self.path == "/events/index":
            authenticated = "misp_session=authenticated" in (self.headers.get("Cookie") or "")
            body = '<a href="/users/logout">Log out</a>' if self.authenticated_marker and authenticated else '<h1>Generic page</h1>'
        elif self.path == "/users/logout":
            type(self).logout_count += 1
            body = "logged out"
        else:
            self.send_error(404)
            return
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        type(self).post_count += 1
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode())
        valid = (
            form.get("csrf") == ["fixture"]
            and form.get("data[User][email]") == ["admin@example.com"]
            and form.get("data[User][password]") == ["fixture-password"]
        )
        if not valid:
            body = b"Invalid username or password"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(307 if self.post_redirect_url else 302)
        self.send_header("Location", self.post_redirect_url or "/events/index")
        if not self.suppress_session_cookie:
            self.send_header("Set-Cookie", "misp_session=authenticated; Path=/; HttpOnly")
        self.end_headers()


class LoginFixture:
    def __init__(self, *, tls=False, authenticated_marker=True, post_redirect_url=None, suppress_session_cookie=False):
        handler = type(
            "ConfiguredLoginFixtureHandler",
            (LoginFixtureHandler,),
            {
                "authenticated_marker": authenticated_marker,
                "post_count": 0,
                "logout_count": 0,
                "post_redirect_url": post_redirect_url,
                "suppress_session_cookie": suppress_session_cookie,
            },
        )
        self.handler = handler
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.tempdir = None
        self.cert_path = None
        if tls:
            if shutil.which("openssl") is None:
                raise unittest.SkipTest("openssl is required for the self-signed TLS fixture")
            self.tempdir = tempfile.TemporaryDirectory()
            cert = Path(self.tempdir.name) / "cert.pem"
            key = Path(self.tempdir.name) / "key.pem"
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", str(key), "-out", str(cert), "-days", "1",
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(cert, key)
            self.cert_path = cert
            self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.scheme = "https" if tls else "http"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"{self.scheme}://localhost:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.tempdir:
            self.tempdir.cleanup()


class LoginSecurityTests(unittest.TestCase):
    def run_check(self, base_url, *args, extra_env=None, credential_value="fixture-password"):
        with tempfile.TemporaryDirectory() as td:
            install_dir = Path(td)
            (install_dir / ".env").write_text(
                f"BASE_URL={base_url}\nADMIN_EMAIL=admin@example.com\nADMIN_PASSWORD={credential_value}\n"
            )
            return subprocess.run(
                [str(LOGIN_CHECK), "--install-dir", str(install_dir), "--machine-readable", *args],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={**os.environ, **(extra_env or {})},
            )

    def test_rejects_plain_http_before_sending_credentials_by_default(self):
        with LoginFixture() as fixture:
            result = self.run_check(fixture.url)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("status=failed", result.stdout)
            self.assertIn("reason=transport-refused", result.stdout)
            self.assertIn("transport_security=not-established", result.stdout)
            self.assertEqual(fixture.handler.post_count, 0)
            self.assertNotIn("fixture-password", result.stdout + result.stderr)

    def test_rejects_conflicting_transport_flags(self):
        result = subprocess.run(
            [str(LOGIN_CHECK), "--strict-tls", "--insecure", "--machine-readable"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot be used together", result.stderr)

    def test_rejects_self_signed_https_before_sending_credentials_by_default(self):
        with LoginFixture(tls=True) as fixture:
            result = self.run_check(fixture.url)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(fixture.handler.post_count, 0)
            self.assertIn("status=failed", result.stdout)
            self.assertIn("reason=tls-verification-failed", result.stdout)
            self.assertIn("transport_security=verified-tls", result.stdout)
            self.assertNotIn("fixture-password", result.stdout + result.stderr)

    def test_verified_https_passes_with_trusted_fixture_certificate(self):
        with LoginFixture(tls=True) as fixture:
            result = self.run_check(
                fixture.url,
                extra_env={"SSL_CERT_FILE": str(fixture.cert_path)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(fixture.handler.post_count, 1)
            self.assertIn("transport_security=verified-tls", result.stdout)
            self.assertIn("authenticated_session_marker=true", result.stdout)
            self.assertNotIn("WARNING:", result.stderr)
            self.assertEqual(fixture.handler.logout_count, 1)

    def test_wrong_password_cannot_produce_authenticated_session(self):
        with LoginFixture() as fixture:
            result = self.run_check(fixture.url, "--insecure", credential_value="wrong-password")
            self.assertEqual(result.returncode, 1)
            self.assertIn("status=failed", result.stdout)
            self.assertIn("authenticated_session_marker=false", result.stdout)
            self.assertEqual(fixture.handler.logout_count, 0)

    def test_missing_session_cookie_cannot_produce_authenticated_session(self):
        with LoginFixture(suppress_session_cookie=True) as fixture:
            result = self.run_check(fixture.url, "--insecure")
            self.assertEqual(result.returncode, 1)
            self.assertIn("reason=no-authenticated-session-marker", result.stdout)
            self.assertEqual(fixture.handler.logout_count, 0)

    def test_explicit_insecure_mode_requires_positive_authenticated_marker(self):
        with LoginFixture(authenticated_marker=False) as fixture:
            result = self.run_check(fixture.url, "--insecure")
            self.assertEqual(fixture.handler.post_count, 1)
            self.assertEqual(result.returncode, 1)
            self.assertIn("status=failed", result.stdout)
            self.assertIn("reason=no-authenticated-session-marker", result.stdout)
            self.assertIn("authenticated_session_marker=false", result.stdout)
            self.assertIn("WARNING:", result.stderr)

    def test_explicit_insecure_mode_passes_only_with_authenticated_marker(self):
        with LoginFixture(authenticated_marker=True) as fixture:
            result = self.run_check(fixture.url, "--insecure")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("status=passed", result.stdout)
            self.assertIn("transport_security=insecure-explicit", result.stdout)
            self.assertIn("authenticated_session_marker=true", result.stdout)
            self.assertNotIn("fixture-password", result.stdout + result.stderr)
            self.assertEqual(fixture.handler.logout_count, 1)

    def test_cross_origin_post_redirect_cannot_replay_credentials(self):
        with LoginFixture() as destination:
            with LoginFixture(post_redirect_url=destination.url + "/users/login") as source:
                result = self.run_check(source.url, "--insecure")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(source.handler.post_count, 1)
                self.assertEqual(destination.handler.post_count, 0)
                self.assertIn("status=failed", result.stdout)
                self.assertIn("reason=cross-origin-redirect", result.stdout)
                self.assertIn("transport_security=insecure-explicit", result.stdout)
                self.assertNotIn("fixture-password", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
