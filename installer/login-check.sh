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
  --machine-readable   Print stable key=value diagnostics for automation/tools
  --ai-output          Alias for --machine-readable
  -h, --help           Show this help
  --version            Show installer version

By default the output is written for human operators. Use --machine-readable
when a script, monitoring job, or AI agent needs stable key=value fields.

The script reads ADMIN_EMAIL and ADMIN_PASSWORD from .env, fetches the login
form, preserves cookies/CSRF hidden fields, posts the credentials, and reports
whether the login appears successful. On success it also performs a best-effort
logout request. It never prints the password.
EOF
}

INSTALL_DIR="/opt/misp-docker"
URL_OVERRIDE=""
STRICT_TLS="false"
MACHINE_READABLE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --url) URL_OVERRIDE="$2"; shift 2;;
    --strict-tls) STRICT_TLS="true"; shift;;
    --machine-readable|--ai-output) MACHINE_READABLE="true"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

ENV_FILE="$INSTALL_DIR/.env"
[[ -f "$ENV_FILE" ]] || fatal "$ENV_FILE missing"

python3 - "$ENV_FILE" "$URL_OVERRIDE" "$STRICT_TLS" "$MACHINE_READABLE" <<'PY'
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

def print_machine(result):
    for key in [
        'status', 'reason', 'login_form_status', 'login_post_status', 'final_path',
        'invalid_credentials_marker', 'csrf_marker', 'server_error_marker',
        'login_success', 'logout_attempted', 'logout_status', 'logout_final_path'
    ]:
        print(f'{key}={result[key]}')

def print_human(result, base_url, email):
    if result['login_success'] == 'true':
        print('✅ MISP Web UI login check passed.')
        print(f'URL: {base_url}')
        print(f'Admin account: {email}')
        print('Password: not printed')
        print(f'Logout: {result["logout_status"]} ({result["logout_final_path"]})')
        return

    print('❌ MISP Web UI login check failed.')
    print(f'URL: {base_url}')
    print(f'Admin account: {email}')
    print('Password: not printed')
    print('')
    print('What happened:')
    if result['reason'] == 'invalid-credentials-or-not-ready':
        print('- MISP returned to the login page with an invalid-credentials marker.')
        print('- Right after a fresh install this can mean MISP is still finishing first-start initialization, even though the login screen is already visible.')
    elif result['reason'] == 'csrf':
        print('- MISP reported a CSRF/session problem.')
    elif result['reason'] == 'server-error':
        print('- MISP returned a server-side error marker during login.')
    elif result['reason'] == 'still-login':
        print('- MISP kept the session on the login page after submitting credentials.')
    else:
        print('- The login request did not reach an authenticated page.')

    print('')
    print('Next steps:')
    print('- If installation is still running, wait until it says: MISP reports interactive login is ready.')
    print('- If installation already completed, re-run: ./installer/doctor.sh --install-dir /opt/misp-docker')
    print('- Verify the generated account with: ./installer/admin-credentials.sh --install-dir /opt/misp-docker')
    print('- To print detailed key=value diagnostics for automation, rerun with --machine-readable.')
    print('')
    print('Diagnostics summary:')
    print(f'- login form HTTP status: {result["login_form_status"]}')
    print(f'- login POST HTTP status: {result["login_post_status"]}')
    print(f'- final path: {result["final_path"]}')
    print(f'- reason: {result["reason"]}')

env_file, url_override, strict_tls, machine_readable = sys.argv[1], sys.argv[2], sys.argv[3] == 'true', sys.argv[4] == 'true'
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

reason = 'ok'
if not success:
    if invalid:
        reason = 'invalid-credentials-or-not-ready'
    elif csrf:
        reason = 'csrf'
    elif server_error:
        reason = 'server-error'
    elif still_login:
        reason = 'still-login'
    else:
        reason = 'unknown'

logout_attempted = False
logout_status = 'not-run'
logout_path = 'not-run'
if success:
    logout_attempted = True
    logout_url = urljoin(base_url + '/', 'users/logout')
    logout_req = Request(logout_url, headers={'User-Agent': 'misp-production-installer-login-check'})
    try:
        with opener.open(logout_req, timeout=30) as response:
            logout_status = str(response.status)
            logout_path = urlparse(response.geturl()).path.rstrip('/') or '/'
    except Exception as exc:
        # Logout should be visible for diagnostics, but a failed logout request
        # should not hide the original login result.
        logout_status = f'failed:{exc.__class__.__name__}'
        logout_path = 'unknown'

result = {
    'status': 'passed' if success else 'failed',
    'reason': reason,
    'login_form_status': str(get_status),
    'login_post_status': str(post_status),
    'final_path': path,
    'invalid_credentials_marker': str(invalid).lower(),
    'csrf_marker': str(csrf).lower(),
    'server_error_marker': str(server_error).lower(),
    'login_success': str(success).lower(),
    'logout_attempted': str(logout_attempted).lower(),
    'logout_status': logout_status,
    'logout_final_path': logout_path,
}

if machine_readable:
    print_machine(result)
else:
    print_human(result, base_url, email)

if not success:
    raise SystemExit(1)
PY
