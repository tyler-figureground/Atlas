# /color-palette-generator

Generates harmonious color palettes from descriptions, moods, images, or reference brands for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Outputs a self-contained HTML file with visual swatches, color codes, contrast ratios, and example pairings.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../../../LICENSE)

## Install

```bash
# Via plugin system
claude plugin marketplace add tyler-figureground/Atlas
claude plugin install 07-presentations@atlas

# Or symlink just this skill
git clone https://github.com/tyler-figureground/Atlas.git
ln -s $(pwd)/Atlas/plugins/07-presentations/skills/color-palette-generator ~/.claude/skills/color-palette-generator
```

## Usage

From a text description:

```
/color-palette-generator warm earth tones for a desert spa
```

From an image:

```
/color-palette-generator ~/Documents/Screenshots/inspiration.png
```

From a single starting color:

```
/color-palette-generator build a palette from #2D5A3D
```

From a brand reference:

```
/color-palette-generator Aesop meets Ace Hotel
```

The skill generates 8-12 colors (primary, secondary, neutral, accent), checks WCAG contrast ratios, and writes a styled `.html` file to `~/Documents/palette-[name-slug].html`.

## What's Included

| File | Purpose |
|------|---------|
| `SKILL.md` | Persona, color theory rules, palette structure, HTML output spec |

## License

MIT
