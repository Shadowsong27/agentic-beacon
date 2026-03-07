# Example Corp Agentic Engineering Warehouse

Centralized repository for coding standards, knowledge, and skills used by AI agents across Example Corp.

## Quick Start

### For Developers

```bash
# Install Beacon CLI
pip install beacon --index-url https://your-pypi.local/simple/

# Setup in your project
cd ~/my-project
abc setup --warehouse ~/path/to/this/repo --all

# Content is distributed to .opencode/ (gitignored)
```

### For Contributors

```bash
# Clone warehouse
git clone <this-repo-url>

# Make changes
# - Add contexts, knowledge, or skills
# - Follow contribution guide

# Submit PR
```

## Structure

- **`contexts/`** - High-level guidance loaded by agents
- **`knowledge/`** - Detailed information organized by type
- **`skills/`** - Reusable workflows and procedures
- **`docs/`** - Warehouse documentation

## Commands

| Command | Description |
|---------|-------------|
| `beacon list` | Show available content |
| `abc setup` | Install content to project |
| `beacon status` | Show what's installed |
| `beacon delta` | Compare project with warehouse |
| `abc update` | Sync from warehouse |

## Documentation

- [Architecture](./docs/architecture.md) - How the warehouse is organized
- [Contribution Guide](./docs/contribution-guide.md) - How to add content

## Maintenance

This warehouse is maintained by Example Corp's Platform Team.

- **Review Frequency:** Quarterly
- **Questions:** Contact platform-team@example.com
- **Issues:** Open an issue in this repository
