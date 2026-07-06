#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Test the configured MISP administrator login without printing the password.

Usage:
  ./installer/login-check.sh [options]

Options:
  --install-dir PATH   Deployment directory (default: /opt/misp-docker)
  --url URL            Override BASE_URL from .env
  --strict-tls         Verify TLS certificates instead of accepting self-signed certs
  -h, --help           Show this help
  --version            Show installer version

The script reads ADMIN_EMAIL and ADMIN_PASSWORD from .env, fetches the login
form, preserves cookies/CSRF hidden fields, posts the credentials, and reports
whether the login appears successful. It never prints the password.
EOF
}

INSTALL_DIR="/opt/misp-docker"
URL_OVERRIDE=""
STRICT_TLS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --url) URL_OVERRIDE="$2"; shift 2;;
    --strict-tls) STRICT_TLS="true"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

ENV_FILE="$INSTALL_DIR/.env"
[[ -f "$ENV_FILE" ]] || fatal "$ENV_FILE missing"

python3 - "$ENV_FILE" "$URL_OVERRIDE" "$STRICT_TLS" <<'PY'
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener
import ssl
import sys

class LoginFormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = {}
        self.password_field = None
        self.email_field = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'input':
            return
        data = {k.lower(): v for k, v in attrs}
        name = data.get('name')
        input_type = (data.get('type') or '').lower()
        if not name:
            return
        if input_type == 'hidden':
            self.hidden[name] = data.get('value', '')
        elif input_type == 'password':
            self.password_field = name
        elif input_type in ('email', 'text') and not self.email_field:
            lowered = name.lower()
            if 'email' in lowered or 'login' in lowered or 'user' in lowered:
                self.email_field = name

def load_env(path):
    values = {}
    for line in Path(path).read_text(errors='ignore').splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key, value = stripped.split('=', 1)
            values[key] = value
    return values

env_file, url_override, strict_tls = sys.argv[1], sys.argv[2], sys.argv[3] == 'true'
values = load_env(env_file)
base_url = (url_override or values.get('BASE_URL') or '').rstrip('/')
email = values.get('ADMIN_EMAIL') or ''
password = values.get('ADMIN_PASSWORD') or ''
if not base_url:
    raise SystemExit('BASE_URL is missing in .env and --url was not provided')
if not email:
    raise SystemExit('ADMIN_EMAIL is missing in .env')
if not password:
    raise SystemExit('ADMIN_PASSWORD is missing in .env')

ctx = ssl.create_default_context() if strict_tls else ssl._create_unverified_context()
opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=ctx))
login_url = urljoin(base_url + '/', 'users/login')

get_req = Request(login_url, headers={'User-Agent': 'misp-production-installer-login-check'})
with opener.open(get_req, timeout=30) as response:
    login_html = response.read().decode('utf-8', errors='replace')
    get_status = response.status

parser = LoginFormParser()
parser.feed(login_html)
email_field = parser.email_field or 'data[User][email]'
password_field = parser.password_field or 'data[User][password]'
form = dict(parser.hidden)
form[email_field] = email
form[password_field] = password
encoded = urlencode(form).encode()
post_req = Request(
    login_url,
    data=encoded,
    headers={
        'User-Agent': 'misp-production-installer-login-check',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': login_url,
    },
)
with opener.open(post_req, timeout=30) as response:
    final_url = response.geturl()
    body = response.read().decode('utf-8', errors='replace')
    post_status = response.status

lower = body.lower()
path = urlparse(final_url).path.rstrip('/') or '/'
invalid = any(marker in lower for marker in ['invalid username', 'invalid password', 'authentication failed', 'login failed'])
csrf = 'csrf' in lower or 'black-holed' in lower
server_error = 'internal error' in lower or 'missingtableexception' in lower or 'stack trace' in lower
still_login = path.endswith('/users/login') and ('password' in lower and 'login' in lower)
success = post_status < 500 and not invalid and not csrf and not server_error and not still_login

print(f'login_form_status={get_status}')
print(f'login_post_status={post_status}')
print(f'final_path={path}')
print(f'invalid_credentials_marker={str(invalid).lower()}')
print(f'csrf_marker={str(csrf).lower()}')
print(f'server_error_marker={str(server_error).lower()}')
print(f'login_success={str(success).lower()}')
if not success:
    raise SystemExit(1)
PY
