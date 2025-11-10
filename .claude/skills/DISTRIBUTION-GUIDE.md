# Agent Architect Skill - Distribution Guide

## Quick Distribution

### Method 1: GitHub Repository
```bash
# Clone or download
git clone <your-repo-url>
cd agent-architect-skill

# Install
cp agent-architect.md ~/.claude/skills/
cp agent-architect-agent.md ~/.claude/agents/agent-architect.md
```

### Method 2: Direct Copy-Paste

**Step 1:** Copy skill file
- Source: `.claude/skills/agent-architect.md`
- Destination: `~/.claude/skills/agent-architect.md`

**Step 2:** Copy agent file
- Source: `.claude/agents/agent-architect.md`
- Destination: `~/.claude/agents/agent-architect.md`

### Method 3: Package Script

Create `install-agent-architect.sh`:

```bash
#!/bin/bash

# Agent Architect Skill Installer
echo "Installing agent-architect skill..."

# Create directories if they don't exist
mkdir -p ~/.claude/skills
mkdir -p ~/.claude/agents

# Copy files
cp agent-architect.md ~/.claude/skills/
cp agent-architect-agent.md ~/.claude/agents/agent-architect.md

echo "✓ Skill installed successfully!"
echo "Usage: Type /agent-architect in Claude Code"
```

## For Distribution

### Package Contents

Create a distribution folder:
```
agent-architect-skill/
├── agent-architect.md              # The skill (UI)
├── agent-architect-agent.md        # The agent (core logic)
├── README.md                       # User documentation
├── DISTRIBUTION-GUIDE.md           # This file
├── EXAMPLE-USAGE.md                # Usage examples
├── install.sh                      # Installation script
└── LICENSE                         # Your license
```

### Sharing Options

#### 1. GitHub Repository
```bash
# Create repo
git init
git add .
git commit -m "Initial release: agent-architect skill"
git remote add origin <your-repo>
git push -u origin main
```

Share URL: `https://github.com/yourusername/agent-architect-skill`

#### 2. GitHub Gist
```bash
# Create gist with both files
gh gist create agent-architect.md agent-architect-agent.md \
  --desc "Agent Architect Skill for Claude Code" \
  --public
```

#### 3. Direct File Sharing
- Zip the package
- Share via cloud storage (Drive, Dropbox)
- Include installation instructions

#### 4. Claude Code Community
- Share in Claude Code Discord/Slack
- Post to Anthropic community forums
- Add to Claude Code skill registry (if exists)

## Example Installation Instructions (for users)

### For macOS/Linux:

```bash
# Download
curl -O https://raw.githubusercontent.com/user/repo/main/agent-architect.md
curl -O https://raw.githubusercontent.com/user/repo/main/agent-architect-agent.md

# Install
mkdir -p ~/.claude/skills ~/.claude/agents
mv agent-architect.md ~/.claude/skills/
mv agent-architect-agent.md ~/.claude/agents/agent-architect.md

# Test
# Restart Claude Code, then type: /agent-architect
```

### For Windows:

```powershell
# Download files from GitHub
# Then copy to:
# %USERPROFILE%\.claude\skills\agent-architect.md
# %USERPROFILE%\.claude\agents\agent-architect.md

# Create directories if needed
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\agents"

# Copy files
Copy-Item agent-architect.md "$env:USERPROFILE\.claude\skills\"
Copy-Item agent-architect-agent.md "$env:USERPROFILE\.claude\agents\agent-architect.md"
```

## Version Management

### Semantic Versioning
- **v1.0.0** - Initial release
- **v1.1.0** - Added features (new questions, better docs)
- **v1.0.1** - Bug fixes (typos, formatting)
- **v2.0.0** - Breaking changes (different agent structure)

### Changelog
Keep a `CHANGELOG.md`:
```markdown
# Changelog

## [1.0.0] - 2025-11-10
### Added
- Initial release
- Interactive questionnaire
- Automatic doc fetching
- Quick and guided modes

### Fixed
- N/A

### Changed
- N/A
```

## Marketing Your Skill

### Description Template
```
🏗️ Agent Architect Skill for Claude Code

Design optimal AI agent systems based on Anthropic best practices and latest
research (Chain-of-Specificity, LIFT-COT).

✨ Features:
- Interactive questionnaire or quick mode
- Auto-loads latest Anthropic documentation
- Research-backed recommendations
- Handles: agent vs skill decisions, optimization, debugging

📦 Easy install: Copy 2 files to ~/.claude/

🚀 Usage: /agent-architect
```

### Tags/Keywords
- claude-code
- ai-agents
- architecture
- anthropic
- skills
- multi-agent-systems
- prompt-engineering

## Support

Provide support information:
- GitHub Issues: `https://github.com/user/repo/issues`
- Discussions: Link to forum/Discord
- Documentation: Link to extended docs
- Contact: Email or social media

## Analytics (Optional)

Track usage without violating privacy:
- GitHub stars/forks
- Download counts
- Issue reports
- Community feedback

## Updates

Notify users of updates:
1. Update version in frontmatter
2. Update CHANGELOG.md
3. Create GitHub release
4. Announce in community channels

## Legal

Include appropriate license:
- MIT (permissive)
- Apache 2.0 (permissive with patent grant)
- GPL (copyleft)
- Proprietary (if not open source)

---

**Ready to distribute!** Package your files and share with the community.
