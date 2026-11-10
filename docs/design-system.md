# Myconomy design system

The interface is built from the tokens in `app/static/css/main.css`. Components use tokens only,
so one change updates the whole site. Dark mode follows the system setting, or the header toggle.

## Tokens

| Group | Tokens | Values |
|---|---|---|
| Type families | `--font-sans`, `--font-mono` | IBM Plex Sans for text. IBM Plex Mono only for large display figures. |
| Type scale | `--text-xs` to `--text-3xl`, `--text-display` | 13, 14, 16, 18, 22, 28, 36 px, and a fluid display size for the headline. |
| Leading | `--leading-tight`, `--leading-body`, `--leading-reading` | 1.15 for headings, 1.6 for text, 1.65 for reading. |
| Space | `--space-1` to `--space-8` | 4, 8, 12, 16, 24, 32, 48, 64 px. Every gap and padding uses these. |
| Radius | `--radius-card`, `--radius-nested`, `--radius-field`, `--radius-pill` | Cards 20 px. Nested boxes take the nested radius. Fields 10 px. Buttons fully round. |
| Colour | `--color-ground`, `--color-panel`, `--color-ink`, `--color-ink-muted`, `--color-line`, `--color-accent`, `--color-value`, `--color-danger` | See below. |
| Motion | `--motion-fast` (160 ms), `--motion-base` (240 ms), `--ease` | Used only for feedback. All motion is removed for reduced-motion users. |

## Rules

1. **Monospace only for large figures.** Labels, tags, table text, and metadata use the sans family.
   Figures in tables use tabular numerals (`font-variant-numeric: tabular-nums`) so columns line up.
2. **No italics for emphasis.** Emphasis comes from weight and colour. `em`, `i`, and `cite` are reset to normal.
3. **No filler.** No decorative badges, eyebrow labels, offset frames, glows, or gradients.
   Tags are used only where they carry meaning, such as status or the illustrative/official label on examples.
4. **Status is never colour alone.** Each status has a dot and words: Current (solid accent dot),
   Stale (outlined dot), Unavailable (grey dot).
5. **One primary action per view.** It uses the orange fill and the large button size. Other actions are secondary.
6. **Nested radius = outer radius − padding.** Cards are 20 px with 16 px padding, so nested boxes (tables, notices,
   formulas) have a 4 px radius. On phones the padding drops to 12 px and the nested radius follows (8 px).
7. **Contrast.** Body text is at least 7:1 on its background. Links are at least 7:1 on white. Status and
   figures are at least 5.8:1 in both themes. Checked with the WCAG contrast formula.
8. **Accent.** Orange marks what the user can act on: primary buttons, the active navigation item, focus
   rings, the current-status dot, and the chart's latest point.
9. **Icons.** There is no icon font. Roadmap steps use numbers, and disclosures use one plus or minus
   sign. Keep new marks in the same style.
10. **Wrapping.** Headings use `text-wrap: balance` and paragraphs use `text-wrap: pretty`.
    The display headline has a small negative optical margin so its large letters sit flush with the text below.
11. **Loading and feedback.** A submitted form shows "Working…" and cannot be submitted twice. Charts show a
    moving bar while loading, and a static message on error. Flash messages fade in. Buttons press down slightly.

## Colour

| Role | Light | Dark |
|---|---|---|
| Page background | `#f5f6f8` | `#07090e` |
| Panel | `#ffffff` | `#10141c` |
| Text | `#0e1219` (18.8:1 on panel) | `#f4f5f7` (16.9:1) |
| Muted text | `#353d4e` (10.9:1) | `#cdd2dc` (12.2:1) |
| Key figures | `#6e4b12` (7.8:1) | `#edcd8c` (12.0:1) |
| Links | `#843d00` (7.9:1) | `#ff951f` (8.4:1) |
| Accent (fills) | `#ff951f` with dark text (8.6:1) | `#ff951f` with dark text (9.1:1) |

## Where things live

- Tokens and components: `app/static/css/main.css`
- Forms and buttons: `app/templates/_macros.html` and each page
- Quick stat widget: `app/templates/_widgets.html`
- Home page preview: `app/services/home_preview.py` (an inline SVG built from stored data)
