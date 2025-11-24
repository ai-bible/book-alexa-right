# Agent Architect Skill for Claude Code

> Design optimal AI agent systems based on Anthropic best practices and latest research

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-orange.svg)]()

## Overview

**agent-architect** is a Claude Code Skill that provides expert guidance on designing, optimizing, and debugging AI agent systems. It combines:

- 🎯 **Interactive questionnaire** for gathering requirements
- 📚 **Automatic documentation loading** from Anthropic
- 🧠 **Specialized agent** with deep architectural expertise
- 🔬 **Research-backed recommendations** (CoS, LIFT-COT papers)

### What is a Claude Code Skill?

Skills are reusable, shareable prompts that expand when invoked. This skill acts as a "wrapper" that:
1. Collects information from you
2. Fetches current best practices
3. Launches a specialized agent for detailed analysis

Think of it as a user-friendly interface to architectural expertise.

## Features

### For Users
- ✅ **Zero configuration** - Works immediately after installation
- ✅ **Two modes** - Quick (direct description) or Guided (questionnaire)
- ✅ **Always current** - Fetches latest Anthropic documentation
- ✅ **Research-backed** - Decisions based on academic papers
- ✅ **Comprehensive** - Covers design, optimization, debugging, learning

### For Architects
- ✅ **Consistent methodology** - Same framework every time
- ✅ **Time-saving** - No manual doc searching
- ✅ **Quality assurance** - Research-driven recommendations
- ✅ **Documentation included** - Built-in access to best practices

### For Maintainers
- ✅ **Single source of truth** - Agent knowledge centralized
- ✅ **Easy updates** - Update agent, skill stays compatible
- ✅ **Portable** - Share one package, works everywhere
- ✅ **Version control** - Track changes via git

## Quick Start

### Installation

**Automatic (recommended):**
```bash
./install.sh
```

**Manual:**
```bash
mkdir -p ~/.claude/skills ~/.claude/agents
cp agent-architect.md ~/.claude/skills/
cp ../agents/agent-architect.md ~/.claude/agents/
```

### Usage

**Quick Mode:**
```
/agent-architect

"I have 7 validators running sequentially. How to parallelize?"
```

**Guided Mode:**
```
/agent-architect

[Answer questionnaire]
```

See [EXAMPLE-USAGE.md](EXAMPLE-USAGE.md) for detailed examples.

## Package Contents

```
agent-architect-skill/
├── agent-architect.md              # The skill (UI)
├── agent-architect-agent.md        # The agent (core logic) - INCLUDED!
├── README.md                       # This file
├── agent-architect-README.md       # Detailed user docs
├── EXAMPLE-USAGE.md                # Usage examples
├── DISTRIBUTION-GUIDE.md           # How to share/distribute
├── install.sh                      # Installation script
└── LICENSE                         # License file
```

## Use Cases

### 🔧 Optimization
- Agent communication hitting token limits
- Sequential workflows are too slow
- Inconsistent constraint adherence

### 🏗️ Design
- Agent vs. skill decision framework
- Multi-agent pipeline architecture
- Validation system design

### 🐛 Debugging
- Information loss in agent handoffs
- Context window overflow
- Missing failure recovery

### 📚 Learning
- Anthropic best practices
- Human-in-the-loop patterns
- Research findings (CoS, LIFT-COT)

## How It Works

```
User: /agent-architect
   ↓
Skill: [Questionnaire or direct input]
   ↓
Claude: [Collects requirements]
   ↓
WebFetch: [Loads Anthropic docs]
   ↓
Task Tool: [Launches agent-architect]
   ↓
Agent: [Analyzes with research + best practices]
   ↓
Claude: [Presents recommendations]
```

## Requirements

**Required:**
- Claude Code with Skill support
- Agent system (Task tool)
- WebFetch capability

**Optional:**
- Git (for version control)
- Internet (for fetching docs)

## Documentation

- **[agent-architect-README.md](agent-architect-README.md)** - Comprehensive user guide
- **[EXAMPLE-USAGE.md](EXAMPLE-USAGE.md)** - Detailed examples with expected outputs
- **[DISTRIBUTION-GUIDE.md](DISTRIBUTION-GUIDE.md)** - How to package and share

## Architecture

### Components

**1. Skill (agent-architect.md)**
- User interface
- Questionnaire logic
- Doc fetching instructions
- Agent launch orchestration

**2. Agent (agent-architect-agent.md → installed as .claude/agents/agent-architect.md)**
- Core architectural expertise (15 KB)
- Research knowledge (CoS, LIFT-COT)
- Anthropic best practices
- Analysis and recommendation engine
- **Self-contained:** Included in package, no external dependencies!

### Design Principles

- **Separation of concerns** - UI (skill) vs logic (agent)
- **Always current** - Fetches latest docs every time
- **Research-backed** - Decisions cite academic papers
- **Portable** - Self-contained package

## Contributing

### Improving the Skill

1. **Better questions** - Edit `agent-architect.md` questionnaire
2. **More examples** - Add to `EXAMPLE-USAGE.md`
3. **Better docs** - Enhance documentation

### Improving the Agent

1. **Update expertise** - Edit `.claude/agents/agent-architect.md`
2. **Add research** - Include new papers/findings
3. **Better patterns** - Document new architectural patterns

### Sharing Improvements

1. Fork the repository
2. Make your changes
3. Submit pull request
4. Or share as gist/alternative version

## Support

**Issues:** [GitHub Issues](https://github.com/yourusername/agent-architect-skill/issues) (update with actual URL)

**Documentation:**
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Agent Patterns](https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns)
- [Multi-Agent Systems](https://docs.anthropic.com/en/docs/build-with-claude/multi-agent-systems)

**Community:**
- Anthropic Discord (update with link)
- Claude Code forums (update with link)

## License

MIT License - See [LICENSE](LICENSE) file

## Changelog

### v1.0.0 (2025-11-10)
- ✨ Initial release
- ✨ Interactive questionnaire
- ✨ Automatic doc fetching
- ✨ Research-backed recommendations
- ✨ Quick and guided modes
- ✨ Complete documentation

## Acknowledgments

Built on:
- **Anthropic's Claude Code** - Platform and best practices
- **CoS Research** (Chain-of-Specificity) - Constraint handling
- **LIFT-COT Research** - Resource management
- **Community feedback** - Real-world use cases

## FAQ

**Q: Do I need internet connection?**
A: Only for fetching latest Anthropic docs. Agent can work offline with cached knowledge.

**Q: Can I customize the questionnaire?**
A: Yes! Edit `agent-architect.md` to change questions.

**Q: How do I update?**
A: Run `./install.sh` again, or manually replace files. Old versions are backed up automatically.

**Q: Can I use this commercially?**
A: Yes, MIT license allows commercial use.

**Q: How is this different from asking Claude directly?**
A: The skill:
- Provides structure (questionnaire)
- Ensures latest docs are loaded
- Triggers specialized agent with full context
- Guarantees consistent methodology

**Q: Can I share this?**
A: Yes! See [DISTRIBUTION-GUIDE.md](DISTRIBUTION-GUIDE.md) for sharing methods.

## What's Next?

After installation:
1. ✅ Type `/agent-architect` in Claude Code
2. ✅ Try Quick Mode with a real problem
3. ✅ Read [EXAMPLE-USAGE.md](EXAMPLE-USAGE.md) for patterns
4. ✅ Share feedback or improvements

---

**Made with ❤️ for the Claude Code community**

*Star ⭐ this project if you find it useful!*
