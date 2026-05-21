#!/usr/bin/env sh
# install.sh — one-liner installer for metis on Linux (and macOS without Homebrew)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/abyssnlp/metis/main/install.sh | sh
#
# What it does:
#   1. Creates a virtualenv at ~/.local/share/metis-venv
#   2. Installs metis-kb from PyPI into that virtualenv
#   3. Symlinks the `metis` binary into ~/.local/bin
#
# Requirements: python3, pip

set -e

INSTALL_DIR="${HOME}/.local/share/metis-venv"
BIN_DIR="${HOME}/.local/bin"
PACKAGE="metis-kb"

# ── checks ────────────────────────────────────────────────────────────────

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required. Install it with your package manager:" >&2
  echo "  Ubuntu/Debian: sudo apt install python3 python3-venv" >&2
  echo "  Fedora/RHEL:   sudo dnf install python3" >&2
  echo "  Arch:          sudo pacman -S python" >&2
  exit 1
fi

PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_MINOR" -lt 9 ]; then
  echo "Error: Python 3.9 or newer is required (found 3.${PYTHON_MINOR})." >&2
  exit 1
fi

# ── install ───────────────────────────────────────────────────────────────

echo "Creating virtualenv at ${INSTALL_DIR} ..."
python3 -m venv "${INSTALL_DIR}"

echo "Installing ${PACKAGE} from PyPI ..."
"${INSTALL_DIR}/bin/pip" install --quiet --upgrade pip
"${INSTALL_DIR}/bin/pip" install --quiet "${PACKAGE}"

echo "Linking binary ..."
mkdir -p "${BIN_DIR}"
ln -sf "${INSTALL_DIR}/bin/metis" "${BIN_DIR}/metis"

# ── path hint ─────────────────────────────────────────────────────────────

if ! echo ":${PATH}:" | grep -q ":${BIN_DIR}:"; then
  echo ""
  echo "NOTE: ${BIN_DIR} is not in your PATH."
  echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
  echo ""
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

echo "Done! Run: metis --help"
