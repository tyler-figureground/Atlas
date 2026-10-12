# Visual Markdown

Mermaid diagrams and collapsible sections in studio Markdown. When they earn their
place, and the rules that keep them honest.

## Where they render

- **VS Code >= 1.121** renders Mermaid natively in the Markdown preview (pan/zoom
  built in). The deprecated `markdown-mermaid` extension and the `mermaid-chart`
  extension conflict with the built-in - do not install them.
- **GitHub** renders Mermaid and `<details>` natively.
- **Google Drive web preview shows raw code.** This drives the first rule below.

## Rules

1. **Words stand alone.** A diagram restates what the text already says; it never
   carries information the text lacks. A reader on Drive web loses nothing but the
   picture.
2. **`flowchart` only.** `mindmap` is experimental in Mermaid; other exotic types
   (`architecture-beta`, `quadrantChart`) are allowed only with a fallback sentence
   beside them.
3. **No `click` links.** Unreliable across renderers (securityLevel restrictions;
   GitHub blocks them). Put a plain text link beside the diagram instead.
4. **One diagram per file**, unless the file's job is being a map (an index README).
   A diagram must earn its lines - reference-set cards stay under their 150-line cap.
5. **Status and severity are words first.** Colour (classDef) may reinforce, never
   carry, a distinction - same rule as ADR 0008.
6. **Node labels under ~25 characters.** Long prose in a node is a table cell that
   wandered off.
7. **`<details>/<summary>`** for depth a first-time reader skips: history, caveats,
   long evidence lists. Not for anything an agent must always read.
8. **Generated, not hand-drawn, where a generator exists.** The Reference Sets map
   and table come from `atlas refs index`, built from card front matter - edit the
   cards, never the block between the `atlas:contents` markers.

## When a diagram earns its place

- The file is an index or a map (Reference Sets README, HOW-TO).
- A workflow with branches (decision points, "if failed then").
- A hierarchy the reader must hold in their head (folder bands, org of a set).

Not for: two-step sequences, lists that read fine as lists, anything an agent parses
(agents read the text; the diagram is for people).
