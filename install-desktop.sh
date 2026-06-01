#!/usr/bin/env bash
# DQE Audit Skill — Desktop Install (macOS)
# Copies the dqe-audit skill to ~/.claude/skills/
# No git required. Uses curl + unzip (both built into macOS).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install-desktop.sh | bash
# Or after manual download:
#   bash install-desktop.sh

set -e

REPO="DQE-SOFTWARE/claude-quality"
BRANCH="main"
ZIP_URL="https://github.com/$REPO/archive/refs/heads/$BRANCH.zip"
TMP_ZIP="/tmp/dqe-quality-$$.zip"
TMP_DIR="/tmp/dqe-quality-install-$$"
TARGET="$HOME/.claude/skills/dqe-audit"

echo ""
echo "=== DQE Audit Skill — Desktop Install (macOS) ==="
echo ""

# Check curl
if ! command -v curl &>/dev/null; then
  echo "ERROR: curl not found. Install Xcode Command Line Tools:"
  echo "  xcode-select --install"
  exit 1
fi

# Check unzip
if ! command -v unzip &>/dev/null; then
  echo "ERROR: unzip not found. Install Xcode Command Line Tools:"
  echo "  xcode-select --install"
  exit 1
fi

# Download ZIP
printf "Downloading from GitHub..."
if ! curl -fsSL "$ZIP_URL" -o "$TMP_ZIP"; then
  echo ""
  echo "ERROR: Could not download from GitHub."
  echo "  Check your internet connection and try again."
  echo "  URL: $ZIP_URL"
  exit 1
fi
echo " OK"

# Extract ZIP
printf "Extracting..."
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
unzip -q "$TMP_ZIP" -d "$TMP_DIR"
echo " OK"

# Locate extracted folder (GitHub adds branch suffix: repo-main/)
EXTRACTED=$(find "$TMP_DIR" -maxdepth 1 -mindepth 1 -type d | head -1)
if [ -z "$EXTRACTED" ]; then
  echo "ERROR: Could not find extracted folder."
  exit 1
fi

SKILL_SRC="$EXTRACTED/skills/dqe-audit"
if [ ! -d "$SKILL_SRC" ]; then
  echo "ERROR: skills/dqe-audit not found in archive."
  exit 1
fi

# Create target and copy
printf "Installing to %s..." "$TARGET"
mkdir -p "$TARGET"
cp -r "$SKILL_SRC/." "$TARGET/"
echo " OK"

# Cleanup
rm -f "$TMP_ZIP"
rm -rf "$TMP_DIR"

echo ""
echo "Skill installed successfully."
echo ""
echo "Restart Claude Code desktop, then use:"
echo "  /dqe-audit ~/path/to/file.csv"
echo ""
echo "Docs: https://github.com/$REPO"
echo ""
