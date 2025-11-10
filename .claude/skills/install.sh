#!/bin/bash

# Agent Architect Skill Installer
# Installs both the skill (UI) and agent (core logic)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKILL_FILE="agent-architect.md"
AGENT_FILE="../agents/agent-architect.md"
SKILL_DIR="$HOME/.claude/skills"
AGENT_DIR="$HOME/.claude/agents"

echo "=========================================="
echo "  Agent Architect Skill Installer"
echo "=========================================="
echo ""

# Check if source files exist
if [ ! -f "$SKILL_FILE" ]; then
    echo -e "${RED}✗ Error: $SKILL_FILE not found${NC}"
    echo "  Make sure you're running this from the .claude/skills directory"
    exit 1
fi

if [ ! -f "$AGENT_FILE" ]; then
    echo -e "${RED}✗ Error: $AGENT_FILE not found${NC}"
    echo "  Make sure the agent file exists at .claude/agents/agent-architect.md"
    exit 1
fi

# Create directories if they don't exist
echo "Creating directories..."
mkdir -p "$SKILL_DIR"
mkdir -p "$AGENT_DIR"
echo -e "${GREEN}✓${NC} Directories ready"
echo ""

# Backup existing files if they exist
if [ -f "$SKILL_DIR/agent-architect.md" ]; then
    BACKUP_FILE="$SKILL_DIR/agent-architect.md.backup.$(date +%Y%m%d-%H%M%S)"
    echo -e "${YELLOW}⚠${NC}  Existing skill found, backing up to:"
    echo "  $BACKUP_FILE"
    cp "$SKILL_DIR/agent-architect.md" "$BACKUP_FILE"
fi

if [ -f "$AGENT_DIR/agent-architect.md" ]; then
    BACKUP_FILE="$AGENT_DIR/agent-architect.md.backup.$(date +%Y%m%d-%H%M%S)"
    echo -e "${YELLOW}⚠${NC}  Existing agent found, backing up to:"
    echo "  $BACKUP_FILE"
    cp "$AGENT_DIR/agent-architect.md" "$BACKUP_FILE"
fi

# Copy files
echo ""
echo "Installing files..."
cp "$SKILL_FILE" "$SKILL_DIR/"
echo -e "${GREEN}✓${NC} Skill installed: $SKILL_DIR/agent-architect.md"

cp "$AGENT_FILE" "$AGENT_DIR/agent-architect.md"
echo -e "${GREEN}✓${NC} Agent installed: $AGENT_DIR/agent-architect.md"

# Success message
echo ""
echo "=========================================="
echo -e "${GREEN}✓ Installation complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code (if running)"
echo "  2. Type: /agent-architect"
echo "  3. Provide your requirements"
echo ""
echo "Documentation:"
echo "  - README: agent-architect-README.md"
echo "  - Examples: EXAMPLE-USAGE.md"
echo "  - Distribution: DISTRIBUTION-GUIDE.md"
echo ""
echo "For help, visit:"
echo "  https://docs.anthropic.com/en/docs/claude-code"
echo ""
