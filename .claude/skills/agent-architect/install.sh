#!/bin/bash

# Agent Architect Skill Installer
# Installs both the skill (directory with SKILL.md) and agent (core logic)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKILL_NAME="agent-architect"
SKILL_FILE="SKILL.md"
AGENT_FILE="agent-architect-agent.md"
SKILLS_DIR="$HOME/.claude/skills"
AGENTS_DIR="$HOME/.claude/agents"

echo "=========================================="
echo "  Agent Architect Skill Installer"
echo "=========================================="
echo ""

# Check if source files exist
if [ ! -f "$SKILL_FILE" ]; then
    echo -e "${RED}✗ Error: $SKILL_FILE not found${NC}"
    echo "  Make sure you're running this from the agent-architect directory"
    exit 1
fi

if [ ! -f "$AGENT_FILE" ]; then
    echo -e "${RED}✗ Error: $AGENT_FILE not found${NC}"
    echo "  Make sure the agent file exists in this directory"
    exit 1
fi

# Create directories if they don't exist
echo "Creating directories..."
mkdir -p "$SKILLS_DIR"
mkdir -p "$AGENTS_DIR"
echo -e "${GREEN}✓${NC} Directories ready"
echo ""

# Backup existing files if they exist
if [ -d "$SKILLS_DIR/$SKILL_NAME" ]; then
    BACKUP_DIR="$SKILLS_DIR/${SKILL_NAME}.backup.$(date +%Y%m%d-%H%M%S)"
    echo -e "${YELLOW}⚠${NC}  Existing skill found, backing up to:"
    echo "  $BACKUP_DIR"
    cp -r "$SKILLS_DIR/$SKILL_NAME" "$BACKUP_DIR"
    rm -rf "$SKILLS_DIR/$SKILL_NAME"
fi

if [ -f "$AGENTS_DIR/agent-architect.md" ]; then
    BACKUP_FILE="$AGENTS_DIR/agent-architect.md.backup.$(date +%Y%m%d-%H%M%S)"
    echo -e "${YELLOW}⚠${NC}  Existing agent found, backing up to:"
    echo "  $BACKUP_FILE"
    cp "$AGENTS_DIR/agent-architect.md" "$BACKUP_FILE"
fi

# Install skill (entire directory structure)
echo ""
echo "Installing skill..."
mkdir -p "$SKILLS_DIR/$SKILL_NAME"
cp SKILL.md "$SKILLS_DIR/$SKILL_NAME/"
cp README.md "$SKILLS_DIR/$SKILL_NAME/"
cp USER-GUIDE.md "$SKILLS_DIR/$SKILL_NAME/" 2>/dev/null || true
echo -e "${GREEN}✓${NC} Skill installed: $SKILLS_DIR/$SKILL_NAME/"

# Install agent
echo ""
echo "Installing agent..."
cp "$AGENT_FILE" "$AGENTS_DIR/agent-architect.md"
echo -e "${GREEN}✓${NC} Agent installed: $AGENTS_DIR/agent-architect.md"

# Success message
echo ""
echo "=========================================="
echo -e "${GREEN}✓ Installation complete!${NC}"
echo "=========================================="
echo ""
echo "Installed:"
echo "  • Skill: $SKILLS_DIR/$SKILL_NAME/"
echo "  • Agent: $AGENTS_DIR/agent-architect.md"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code (if running)"
echo "  2. Type: /agent-architect"
echo "  3. Provide your requirements"
echo ""
echo "Documentation:"
echo "  - README: $SKILLS_DIR/$SKILL_NAME/README.md"
echo "  - User Guide: $SKILLS_DIR/$SKILL_NAME/USER-GUIDE.md"
echo "  - Examples: EXAMPLE-USAGE.md (in this directory)"
echo ""
echo "For help, visit:"
echo "  https://docs.anthropic.com/en/docs/claude-code"
echo ""
