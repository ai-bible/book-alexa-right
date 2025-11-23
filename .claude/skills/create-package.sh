#!/bin/bash

# Agent Architect Skill - Package Creator
# Creates distribution package for sharing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get version from argument or use default
VERSION="${1:-v1.0.0}"
PACKAGE_NAME="agent-architect-skill-${VERSION}"

echo "=========================================="
echo "  Agent Architect Skill - Package Creator"
echo "=========================================="
echo ""
echo -e "${BLUE}Version:${NC} $VERSION"
echo ""

# Check if files exist
REQUIRED_FILES=(
    "agent-architect.md"
    "agent-architect-agent.md"
    "README.md"
    "LICENSE"
)

echo "Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ Error: Required file not found: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓${NC} All required files present"
echo ""

# Create package directory
echo "Creating package directory..."
rm -rf "$PACKAGE_NAME"
mkdir -p "$PACKAGE_NAME/agent"
echo -e "${GREEN}✓${NC} Directory created: $PACKAGE_NAME/"
echo ""

# Copy files
echo "Copying files..."

# Core skill
cp agent-architect.md "$PACKAGE_NAME/"
echo "  → agent-architect.md"

# Agent
cp agent-architect-agent.md "$PACKAGE_NAME/agent/"
# Rename to standard agent name
mv "$PACKAGE_NAME/agent/agent-architect-agent.md" "$PACKAGE_NAME/agent/agent-architect.md"
echo "  → agent/agent-architect.md"

# Documentation
DOCS=(
    "README.md"
    "agent-architect-README.md"
    "EXAMPLE-USAGE.md"
    "DISTRIBUTION-GUIDE.md"
    "LICENSE"
    "CHANGELOG.md"
    "PACKAGE.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        cp "$doc" "$PACKAGE_NAME/"
        echo "  → $doc"
    else
        echo -e "  ${YELLOW}⚠${NC} Skipping (not found): $doc"
    fi
done

# Installation script (with modified paths)
if [ -f "install.sh" ]; then
    cp install.sh "$PACKAGE_NAME/"
    # Update AGENT_FILE path in install script
    sed -i.bak 's|AGENT_FILE="../agents/agent-architect.md"|AGENT_FILE="agent/agent-architect.md"|g' "$PACKAGE_NAME/install.sh"
    rm "$PACKAGE_NAME/install.sh.bak" 2>/dev/null || true
    chmod +x "$PACKAGE_NAME/install.sh"
    echo "  → install.sh (paths updated)"
fi

echo ""
echo -e "${GREEN}✓${NC} Files copied successfully"
echo ""

# Create archives
echo "Creating archives..."

# Tar.gz
tar czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
SIZE_TGZ=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)
echo -e "${GREEN}✓${NC} Created: ${PACKAGE_NAME}.tar.gz (${SIZE_TGZ})"

# Zip
if command -v zip &> /dev/null; then
    zip -qr "${PACKAGE_NAME}.zip" "$PACKAGE_NAME"
    SIZE_ZIP=$(du -h "${PACKAGE_NAME}.zip" | cut -f1)
    echo -e "${GREEN}✓${NC} Created: ${PACKAGE_NAME}.zip (${SIZE_ZIP})"
else
    echo -e "${YELLOW}⚠${NC} zip command not found, skipping .zip creation"
fi

echo ""

# Calculate checksums
echo "Generating checksums..."
if command -v sha256sum &> /dev/null; then
    sha256sum "${PACKAGE_NAME}.tar.gz" > "${PACKAGE_NAME}.tar.gz.sha256"
    echo -e "${GREEN}✓${NC} SHA256: ${PACKAGE_NAME}.tar.gz.sha256"
    if [ -f "${PACKAGE_NAME}.zip" ]; then
        sha256sum "${PACKAGE_NAME}.zip" > "${PACKAGE_NAME}.zip.sha256"
        echo -e "${GREEN}✓${NC} SHA256: ${PACKAGE_NAME}.zip.sha256"
    fi
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}✓ Package created successfully!${NC}"
echo "=========================================="
echo ""
echo "Distribution files:"
echo "  • ${PACKAGE_NAME}.tar.gz (${SIZE_TGZ})"
if [ -f "${PACKAGE_NAME}.zip" ]; then
    echo "  • ${PACKAGE_NAME}.zip (${SIZE_ZIP})"
fi
echo "  • ${PACKAGE_NAME}/ (directory)"
echo ""
echo "Next steps:"
echo "  1. Test installation:"
echo "     cd ${PACKAGE_NAME} && ./install.sh"
echo ""
echo "  2. Distribute via:"
echo "     • GitHub Release: gh release create ${VERSION} ${PACKAGE_NAME}.tar.gz"
echo "     • Direct share: Upload .tar.gz or .zip"
echo "     • Gist: gh gist create agent-architect.md agent/agent-architect.md"
echo ""
echo "  3. Verify package:"
echo "     tar tzf ${PACKAGE_NAME}.tar.gz | head -20"
echo ""
echo "Documentation:"
echo "  • DISTRIBUTION-GUIDE.md - Distribution methods"
echo "  • PACKAGE.md - Complete packaging guide"
echo ""

# Offer to create GitHub release
if command -v gh &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
    echo ""
    read -p "Create GitHub release? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Creating GitHub tag and release..."

        # Check if tag exists
        if git rev-parse "$VERSION" >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠${NC} Tag $VERSION already exists"
        else
            git tag -a "$VERSION" -m "Release $VERSION"
            git push origin "$VERSION"
            echo -e "${GREEN}✓${NC} Tag created and pushed"
        fi

        # Create release
        gh release create "$VERSION" \
            "${PACKAGE_NAME}.tar.gz" \
            --title "Agent Architect Skill ${VERSION}" \
            --notes "See CHANGELOG.md for details." \
            --latest

        echo -e "${GREEN}✓${NC} GitHub release created!"
        echo ""
        echo "Release URL: $(gh release view $VERSION --json url -q .url)"
    fi
fi

echo ""
echo "Package ready for distribution! 🎉"
echo ""
