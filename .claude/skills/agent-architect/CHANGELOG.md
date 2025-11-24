# Changelog

All notable changes to the Agent Architect Skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Community examples section
- Video tutorial
- Integration with Claude Code skill registry (when available)

## [1.0.0] - 2025-11-10

### Added
- Initial release of agent-architect skill
- Interactive questionnaire for guided mode
- Quick mode for direct problem description
- Automatic fetching of Anthropic documentation
  - Agent patterns
  - Multi-agent systems
  - Prompt engineering
- **Self-contained package:** Agent included (agent-architect-agent.md)
- Integration with agent-architect agent via Task tool
- Research-backed decision framework
  - Chain-of-Specificity (CoS) principles
  - LIFT-COT resource management patterns
- Common scenarios section with examples
- Quick decision framework reference
- Installation script (install.sh)
- Comprehensive documentation
  - Main README
  - User guide (agent-architect-README.md)
  - Usage examples (EXAMPLE-USAGE.md)
  - Distribution guide (DISTRIBUTION-GUIDE.md)
- MIT License
- This CHANGELOG

### Architecture
- Skill (UI layer) + Agent (logic layer) separation
- File-based artifact communication
- Support for both modes (quick/guided)
- Automatic documentation loading via WebFetch
- Task tool integration for agent launching

### Documentation
- 4 example scenarios with detailed outputs
- Common patterns identification
- Troubleshooting section
- FAQ section
- Installation instructions for multiple platforms

### Distribution
- Install script with backup functionality
- GitHub repository structure
- Package guidelines
- Version management system

## Version History Summary

| Version | Date | Key Features |
|---------|------|--------------|
| 1.0.0 | 2025-11-10 | Initial release with questionnaire, doc fetching, agent integration |

---

## How to Read This Changelog

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security vulnerability fixes

## Contributing

When submitting changes:
1. Update this CHANGELOG under [Unreleased] section
2. Follow the format above
3. Include version bump in your PR title
4. Move [Unreleased] items to new version section on release

## Release Process

1. Update CHANGELOG: Move [Unreleased] to new [X.Y.Z] section
2. Update version in README badges
3. Update version in skill frontmatter (if present)
4. Create git tag: `git tag v1.0.0`
5. Push tag: `git push origin v1.0.0`
6. Create GitHub release with CHANGELOG excerpt
7. Announce in community channels

---

**Questions about versioning?** See [Semantic Versioning](https://semver.org/)

**Questions about changelog format?** See [Keep a Changelog](https://keepachangelog.com/)
