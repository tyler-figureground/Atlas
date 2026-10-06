# /product-pair

Suggest complementary products that pair well with a given item — side tables for sofas, task lights for desks, etc. for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../../../LICENSE)

## Install

```bash
# Via plugin system
claude plugin marketplace add tyler-figureground/Atlas
claude plugin install 06-materials-research@atlas

# Or symlink just this skill
git clone https://github.com/tyler-figureground/Atlas.git
ln -s $(pwd)/Atlas/plugins/06-materials-research/skills/product-pair ~/.claude/skills/product-pair
```

## Usage

```
/product-pair
```

## What's Included

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and implementation |

## License

MIT
