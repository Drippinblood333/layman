#!/usr/bin/env sh
set -eu

REPOSITORY="${LAYMAN_REPOSITORY:-Drippinblood333/layman}"
VERSION="${LAYMAN_VERSION:-latest}"
MODE="${LAYMAN_MODE:-auto}"
case "$(uname -s)" in
  Darwin) os=macos ;;
  Linux) os=linux ;;
  *) echo "Unsupported operating system" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  arm64|aarch64) arch=arm64 ;;
  x86_64|amd64) arch=x64 ;;
  *) echo "Unsupported architecture" >&2; exit 1 ;;
esac
asset="layman-${os}-${arch}.zip"
api="https://api.github.com/repos/${REPOSITORY}/releases"
if [ "$VERSION" = latest ]; then
  latest=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/${REPOSITORY}/releases/latest")
  VERSION=${latest##*/}
fi
url="https://github.com/${REPOSITORY}/releases/download/${VERSION}/${asset}"
checksums_url="https://github.com/${REPOSITORY}/releases/download/${VERSION}/SHA256SUMS.txt"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -H 'User-Agent: Layman-Installer' "$url" -o "$tmp/$asset"
curl -fsSL -H 'User-Agent: Layman-Installer' "$checksums_url" -o "$tmp/SHA256SUMS.txt"
expected=$(awk -v name="$asset" '$2 == name { print toupper($1); exit }' "$tmp/SHA256SUMS.txt")
if [ -z "$expected" ]; then echo "Checksum entry not found for $asset" >&2; exit 1; fi
if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum "$tmp/$asset" | awk '{ print toupper($1) }')
elif command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 "$tmp/$asset" | awk '{ print toupper($1) }')
else
  echo 'No SHA-256 utility found (sha256sum or shasum required)' >&2; exit 1
fi
if [ "$actual" != "$expected" ]; then echo "SHA-256 verification failed for $asset" >&2; exit 1; fi
unzip -q "$tmp/$asset" -d "$tmp/unpacked"
mkdir -p "$HOME/.local/bin"
install -m 755 "$tmp/unpacked/layman" "$HOME/.local/bin/layman"
echo "Installed Layman to $HOME/.local/bin/layman"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo 'Add $HOME/.local/bin to PATH.' ;; esac
"$HOME/.local/bin/layman" setup --mode "$MODE"
echo 'Restart Codex and open a new task so the updated plugin and PATH are loaded.'
