#!/usr/bin/env bash
# DQE Audit Plugin — Installation guide
# See: https://github.com/DQE-SOFTWARE/claude-quality

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== DQE Audit Plugin — dqe-quality ==="
echo ""

# Check Claude Code is available
if ! command -v claude &>/dev/null; then
  echo "❌ Claude Code CLI not found. Install it first:"
  echo "   https://claude.ai/code"
  exit 1
fi

echo "Choose your installation method:"
echo ""
echo "  [1] Local test (current session only)"
echo "      claude --plugin-dir \"$REPO_DIR\""
echo ""
echo "  [2] Install from community marketplace"
echo "      /plugin marketplace add anthropics/claude-plugins-community"
echo "      /plugin install dqe-quality"
echo ""
echo "  [3] Install directly from this local repo"
echo "      /plugin marketplace add \"$REPO_DIR\""
echo "      /plugin install dqe-quality"
echo ""

echo "After installation, use:"
echo "   /dqe-quality:dqe-audit <path/to/file.csv>"
echo ""
echo "Docs: https://github.com/DQE-SOFTWARE/claude-quality"
