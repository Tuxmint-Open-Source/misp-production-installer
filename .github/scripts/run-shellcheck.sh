#!/usr/bin/env bash
set -euo pipefail

readonly SHELLCHECK_VERSION="0.11.0"
readonly SHELLCHECK_PLATFORM="linux.x86_64"
readonly SHELLCHECK_ARCHIVE="shellcheck-v${SHELLCHECK_VERSION}.${SHELLCHECK_PLATFORM}.tar.xz"
readonly SHELLCHECK_SHA256="8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198"
readonly SHELLCHECK_URL="https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/${SHELLCHECK_ARCHIVE}"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  printf 'Unsupported ShellCheck runner platform: %s/%s\n' "$(uname -s)" "$(uname -m)" >&2
  exit 1
fi

workdir="$(mktemp -d)"
trap 'rm -rf -- "$workdir"' EXIT
archive_path="${workdir}/${SHELLCHECK_ARCHIVE}"

curl \
  --fail \
  --location \
  --proto '=https' \
  --tlsv1.2 \
  --retry 3 \
  --retry-all-errors \
  --silent \
  --show-error \
  --output "$archive_path" \
  "$SHELLCHECK_URL"

printf '%s  %s\n' "$SHELLCHECK_SHA256" "$archive_path" | sha256sum --check --strict -

tar --extract --xz --file "$archive_path" --directory "$workdir"
shellcheck_bin="${workdir}/shellcheck-v${SHELLCHECK_VERSION}/shellcheck"
if [[ ! -x "$shellcheck_bin" ]]; then
  printf 'Verified ShellCheck archive did not contain the expected executable.\n' >&2
  exit 1
fi

actual_version="$($shellcheck_bin --version | awk '$1 == "version:" {print $2}')"
if [[ "$actual_version" != "$SHELLCHECK_VERSION" ]]; then
  printf 'ShellCheck version mismatch: expected %s, got %s\n' "$SHELLCHECK_VERSION" "$actual_version" >&2
  exit 1
fi

scripts_inventory="${workdir}/lifecycle-scripts.nul"
if ! find lifecycle -type f -name '*.sh' -print0 | sort -z >"$scripts_inventory"; then
  printf 'Failed to build the complete lifecycle shell-script inventory.\n' >&2
  exit 1
fi

declare -a scripts=()
while IFS= read -r -d '' script; do
  scripts+=("$script")
done <"$scripts_inventory"

if (( ${#scripts[@]} == 0 )); then
  printf 'No lifecycle shell scripts found.\n' >&2
  exit 1
fi

"$shellcheck_bin" --format=gcc --severity=error "${scripts[@]}"
