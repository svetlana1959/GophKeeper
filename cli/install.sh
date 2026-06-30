#!/usr/bin/env sh
# Quick install for the goph CLI (Linux / macOS).
#   curl -sSL https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.sh | sh
#
# Override the install location with INSTALL_DIR (default: /usr/local/bin):
#   curl -sSL .../install.sh | INSTALL_DIR="$HOME/.local/bin" sh

set -eu

REPO="svetlana1959/GophKeeper"
BINARY="goph"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"

# --- detect OS -------------------------------------------------------------
os="$(uname -s)"
case "$os" in
	Linux)  OS="linux" ;;
	Darwin) OS="darwin" ;;
	*) echo "Unsupported OS: $os" >&2; exit 1 ;;
esac

# --- detect arch (normalise to GoReleaser's goarch names) ------------------
arch="$(uname -m)"
case "$arch" in
	x86_64 | amd64)  ARCH="amd64" ;;
	aarch64 | arm64) ARCH="arm64" ;;
	*) echo "Unsupported architecture: $arch" >&2; exit 1 ;;
esac

# --- resolve the latest release tag via the GitHub API ---------------------
TAG="$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" \
	| grep '"tag_name"' | head -n1 | cut -d'"' -f4)"
if [ -z "$TAG" ]; then
	echo "Could not determine the latest release tag." >&2
	exit 1
fi
VERSION="${TAG#v}" # archive names drop the leading "v"

# --- build the download URL (matches .goreleaser.yaml name_template) -------
ASSET="${BINARY}_${VERSION}_${OS}_${ARCH}.tar.gz"
URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"

echo "Installing ${BINARY} ${TAG} (${OS}/${ARCH})..."

# --- download + extract into a temp dir we always clean up -----------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if ! curl -fsSL "$URL" | tar -xz -C "$TMP"; then
	echo "Download failed: $URL" >&2
	exit 1
fi

# --- decide whether we need sudo by actually probing for write access ------
# Walk up to the first directory that exists, then try to create a temp file
# there. A real write proves access where a permission-bit check ([ -w ]) can
# be fooled by read-only mounts, NFS root-squash, or ACLs.
probe="$INSTALL_DIR"
while [ ! -d "$probe" ] && [ "$probe" != "/" ]; do
	probe="$(dirname "$probe")"
done

if touch "$probe/.${BINARY}_write_test_$$" 2>/dev/null; then
	rm -f "$probe/.${BINARY}_write_test_$$"
	SUDO=""
elif command -v sudo >/dev/null 2>&1; then
	echo "Elevating with sudo to write to ${INSTALL_DIR}"
	SUDO="sudo"
else
	echo "Cannot write to ${INSTALL_DIR} and sudo is unavailable." >&2
	echo "Re-run with a writable location, e.g.:" >&2
	echo "  curl -sSL .../install.sh | INSTALL_DIR=\"\$HOME/.local/bin\" sh" >&2
	exit 1
fi

$SUDO mkdir -p "$INSTALL_DIR"
$SUDO install -m 0755 "$TMP/${BINARY}" "$INSTALL_DIR/${BINARY}"

echo "Installed ${BINARY} to ${INSTALL_DIR}/${BINARY}"

# --- warn if the install dir isn't on PATH --------------------------------
case ":$PATH:" in
	*":$INSTALL_DIR:"*) ;;
	*)
		echo "Note: ${INSTALL_DIR} is not on your PATH. Add this to your shell profile:"
		echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
		;;
esac
