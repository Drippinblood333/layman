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
binary_stage=
notice_stage=
notice_backup=
cleanup() {
  rm -rf "$tmp"
  if [ -n "$binary_stage" ]; then rm -f "$binary_stage"; fi
  if [ -n "$notice_stage" ]; then rm -rf "$notice_stage"; fi
  # A nonempty backup means restoration failed: never delete that evidence.
  if [ -n "$notice_backup" ]; then rmdir "$notice_backup" 2>/dev/null || :; fi
}
trap cleanup 0
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
for name in layman BUILD.json bundle-audit.json runtime-dependencies.json standalone-components.json THIRD_PARTY_NOTICES.md; do
  if [ ! -f "$tmp/unpacked/$name" ]; then echo "Required package file not found: $name" >&2; exit 1; fi
done
if [ ! -d "$tmp/unpacked/THIRD_PARTY_LICENSES" ]; then echo 'Required package directory not found: THIRD_PARTY_LICENSES' >&2; exit 1; fi
notice_root="${XDG_DATA_HOME:-$HOME/.local/share}/layman/installation"
binary_root="$HOME/.local/bin"
mkdir -p "$(dirname "$notice_root")" "$binary_root"
if [ -d "$binary_root/layman" ]; then echo 'Executable destination is a directory' >&2; exit 1; fi
# Prepare both destinations before changing either installed component.
binary_stage=$(mktemp "$binary_root/.layman-stage.XXXXXX")
install -m 755 "$tmp/unpacked/layman" "$binary_stage"
notice_stage=$(mktemp -d "$(dirname "$notice_root")/.installation-stage.XXXXXX")
if [ -d "$notice_root" ]; then cp -R "$notice_root/." "$notice_stage/"; fi
for name in BUILD.json bundle-audit.json runtime-dependencies.json standalone-components.json THIRD_PARTY_NOTICES.md; do
  cp "$tmp/unpacked/$name" "$notice_stage/$name"
done
cp -R "$tmp/unpacked/THIRD_PARTY_LICENSES" "$notice_stage/"
notice_backup=$(mktemp -d "$(dirname "$notice_root")/.installation-backup.XXXXXX")
notice_saved=0
notice_switched=0
restore_notices() {
  if [ "$notice_switched" = 1 ]; then
    if ! mv "$notice_root" "$notice_stage"; then
      echo "Could not restore records; preserved backup: $notice_backup" >&2; return 1
    fi
  fi
  if [ "$notice_saved" = 1 ]; then
    if ! mv "$notice_backup/installation" "$notice_root"; then
      echo "Could not restore records; preserved backup: $notice_backup" >&2; return 1
    fi
  fi
}
if [ -e "$notice_root" ] || [ -L "$notice_root" ]; then
  mv "$notice_root" "$notice_backup/installation"
  notice_saved=1
fi
if ! mv "$notice_stage" "$notice_root"; then restore_notices; exit 1; fi
notice_switched=1
# Same-directory rename leaves the old binary intact if the commit fails.
if ! mv "$binary_stage" "$binary_root/layman"; then restore_notices; exit 1; fi
if ! rm -rf "$notice_backup"; then echo "Old records backup remains: $notice_backup" >&2; fi
echo "Installed Layman to $HOME/.local/bin/layman"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo 'Add $HOME/.local/bin to PATH.' ;; esac
"$HOME/.local/bin/layman" setup --mode "$MODE"
echo 'Restart Codex and open a new task so the updated plugin and PATH are loaded.'
