# Agent Architect Skill - Distribution Package

## Overview

The **agent-architect** skill is a wrapper that makes AI agent architecture expertise easily accessible. It combines:
- Interactive questionnaire for gathering requirements
- Automatic loading of latest Anthropic documentation
- Specialized agent-architect for detailed architectural analysis

## What's Included

- `agent-architect.md` - The main skill file (Claude Code Skill format)
- `.claude/agents/agent-architect.md` - The underlying agent (full architectural expertise)
- This README

## Installation

### For Claude Code Users

1. **Copy the skill file:**
   ```bash
   cp agent-architect.md ~/.claude/skills/
   ```

2. **Copy the agent file:**
   ```bash
   mkdir -p ~/.claude/agents/
   cp ../agents/agent-architect.md ~/.claude/agents/
   ```

3. **Restart Claude Code** (if running)

4. **Verify installation:**
   Type `/agent-architect` in Claude Code - you should see the skill expand with the questionnaire.

### For Projects

Include in your project's `.claude/` directory:

```
your-project/
├── .claude/
│   ├── skills/
│   │   └── agent-architect.md          ← Skill (user interface)
│   └── agents/
│       └── agent-architect.md          ← Agent (core expertise)
└── ...
```

## Usage

### Quick Start
```
User: /agent-architect
Skill: [Questionnaire appears]
User: "I have 7 validators running sequentially. How to parallelize?"
Claude: [Fetches docs] → [Launches agent] → [Returns recommendations]
```

### Direct Mode
```
User: /agent-architect
User: "Design a multi-agent pipeline for content validation with 5+ constraints"
Claude: [Proceeds immediately with analysis]
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User triggers skill: /agent-architect                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Skill presents questionnaire (or accepts direct input)   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Claude collects requirements                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. WebFetch loads Anthropic docs:                           │
│    - Agent patterns                                          │
│    - Multi-agent systems                                     │
│    - Prompt engineering                                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Task tool launches agent-architect with:                 │
│    - User requirements                                       │
│    - Fetched documentation                                   │
│    - Research papers (CoS, LIFT-COT)                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Agent analyzes and returns:                              │
│    - Recommended architecture                                │
│    - Research justification                                  │
│    - Implementation guidance                                 │
│    - Potential issues                                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Claude presents results to user                          │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### For End Users
- **No setup needed** - Just type `/agent-architect`
- **Guided experience** - Interactive questionnaire or direct input
- **Current best practices** - Always fetches latest Anthropic docs
- **Research-backed** - Recommendations based on academic papers (CoS, LIFT-COT)

### For Maintainers
- **Single source of truth** - Agent knowledge is in one place
- **Easy updates** - Update agent file, skill stays the same
- **Portable** - Share one file, works everywhere
- **Versioned** - Can track changes via git

### For Architects
- **Consistent methodology** - Same framework for every project
- **Documentation included** - Built-in access to Anthropic docs
- **Time saver** - No need to manually search for best practices
- **Quality assurance** - Research-driven recommendations

## Dependencies

**Required:**
- Claude Code with Skill support
- Agent system (Task tool with sub-agents)
- WebFetch capability (for loading docs)

**Optional:**
- Git (for version control)
- Internet connection (for fetching latest docs)

## Configuration

No configuration needed! The skill works out of the box.

**Optional customization:**
- Edit `agent-architect.md` (skill) to change questionnaire
- Edit `.claude/agents/agent-architect.md` to adjust agent expertise
- Add custom documentation URLs in Step 2

## Troubleshooting

### Skill doesn't appear
- Verify file is in `.claude/skills/agent-architect.md`
- Check frontmatter format (name, description)
- Restart Claude Code

### Agent not launching
- Verify agent file exists in `.claude/agents/agent-architect.md`
- Check Task tool is available
- Review error messages

### Documentation not loading
- Check internet connection
- Verify URLs are accessible
- Use cached knowledge if WebFetch fails

## Contributing

To improve this skill:

1. **Enhance questionnaire** - Add/refine questions in skill file
2. **Update agent** - Improve architectural expertise in agent file
3. **Add documentation sources** - Include more relevant URLs
4. **Share examples** - Add common scenarios section

## License

Same as the project this skill belongs to.

## Support

For issues or questions:
- Check Claude Code documentation
- Review Anthropic agent patterns docs
- Open issue in your project repository

## Version History

- **v1.0** (2025-11-10): Initial release
  - Interactive questionnaire
  - Automatic doc fetching
  - Agent integration
  - Quick and guided modes

---

**Ready to use!** Copy the files to your `.claude/` directory and type `/agent-architect` in Claude Code.
