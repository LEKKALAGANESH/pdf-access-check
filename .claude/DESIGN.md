# DESIGN — civic paper-form look

Source of truth: `static/style.css :root`. Use tokens; never hardcode a new color or size.

## Color
| Token | Value | Use |
|---|---|---|
| `--ink` | #1a2433 | body text, strong borders |
| `--ink-soft` | #46546a | secondary text, input borders |
| `--paper` | #f5f8fa | page background |
| `--sheet` | #ffffff | cards, inputs, checks list |
| `--civic` / `--civic-dark` | #0a5c6b / #074652 | buttons, deadline rule / hover |
| `--pass` / `--fail` | #1e6b3a / #a4262c | pass and fail states |
| `--muted` | #5d6b7e | rule codes, footnotes |
| `--line` | #c9d3dc | dividers |
| `--highlight` | #ffe27a | focus halo |
More tokens: `--link` #074652, `--on-civic` #fff, `--close` #8a4b00 (Needs work), `--fail-bg` #fdf1f1,
`--over` #fff8d6 (drag over), `--disabled` #5d6b7e, `--quiet-edge` #0a5c6b.
Dark theme: `@media screen and (prefers-color-scheme: dark)` redefines the same tokens (paper #0e151c, sheet #16202a,
ink #e7edf3, link #7cc8d6, pass #6fd393, fail #ff8f8f, close #f2b45c); print always uses the light palette.

## Type
Public Sans (self-hosted variable woff2), body 1.0625rem/1.55. h1 clamp(2rem…3.25rem) 800,
h2 clamp(1.375rem…1.75rem) 750, h3 1.25rem 700. Line length `--measure: 68ch`.

## Space
`--space-1..6` = 0.25 / 0.5 / 1 / 1.5 / 2.5 / 4 rem. Content width min(100% − 2rem, 52rem).

## Components
- Drop zone: white sheet, 2px dashed border; solid + yellow tint while dragging.
- Button: 48px min height, `--radius-control` 6px, civic fill; grey + progress cursor when disabled.
- Score stamp: 5px double border in the verdict color; the one loud element on the page.
- Check row: grid 6.5rem status column + body; stacks under 30rem.
- Error box: 4px left fail border on pale red. Done box: 6px left pass border.
- Quiet button (`.button-quiet`): outlined, 44px, for secondary actions (copy link, print). Never two filled buttons side by side.
- Link button (`.link-button`): text button inside tables; `aria-current="true"` marks the row shown.
- Data table (`.table-scroll` > `.data-table`): scrolls sideways inside its frame, never the page.
- Focus: 3px ink outline + 6px highlight halo on every focusable element.
- `[hidden]` always wins over component `display` rules.
