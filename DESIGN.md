---
version: alpha
name: Monkey-Puzzle-design-system
description: A friendly, calm, single-brand survey and result experience on Bootstrap 5.3 with a custom layer (app/static/css/theme.css). One green brand colour, native HTML/CSS controls with no JavaScript for selection, automatic light and dark appearance, and results designed to be shared (web page, PDF, email, 1200x630 share card, 1200x1200 certificate). Colour is never the only carrier of meaning: relationships use border patterns, bands use text labels, and personas use line-art icons.

# Source of truth is theme.css :root. Persona and band content lives in content/survey.yaml.
colors:
  # Brand
  brand-primary: "#2e7d32"        # Fill: selected grid cell, certificate and share-card accent. White text 5.13:1.
  button-success: "#2e7d32"       # Primary buttons (Begin, Next and others) use brand-primary.
  brand-primary-dark: "#1b5e20"   # Selected-cell border. White text 7.87:1.
  brand-accent-light: "#2e7d32"   # Text, border and outline green on light surfaces (same value as primary).
  brand-accent-dark: "#81c784"    # Text, border and outline green on dark surfaces. 7.67:1 on #212529.
  # Surfaces (light / dark)
  surface: "#ffffff"
  surface-dark: "#212529"
  border: "#dee2e6"
  border-dark: "#495057"
  muted-border: "#eeeeee"
  muted-border-dark: "#343a40"
  strong-text: "#212529"
  strong-text-dark: "#f8f9fa"
  header-text: "#495057"          # 8.18:1 on white
  header-text-dark: "#ced4da"
  muted-text: "#6c757d"           # 4.69:1 on white. Do not go lighter.
  muted-text-dark: "#adb5bd"      # 7.43:1 on #212529
  selected-tint: "rgba(46, 125, 50, 0.08)"
  selected-tint-dark: "rgba(129, 199, 132, 0.16)"
  # Relationship colours on the result grid (always paired with a border style, see Rules)
  rel-ally: "#1565c0"
  rel-ally-tint: "#e3eefb"
  rel-friend: "#00838f"
  rel-friend-tint: "#ddf0f1"
  rel-necessity: "#7b1fa2"
  rel-necessity-tint: "#f3e6f8"
  # Innovation-curve bands (data, editable in content/survey.yaml by Rob and Andrew)
  band-laggards: "#c0392b"
  band-late-majority: "#e67e22"
  band-early-majority: "#f1c40f"
  band-early-adopters: "#7cb342"
  band-innovators: "#2e7d32"

typography:
  family: "Bootstrap 5.3 system stack (no custom webfont)"
  body: { fontSize: 1rem, lineHeight: 1.5 }
  option-card: { fontSize: 1rem, selected: 600 }
  spectrum-node: { fontSize: 0.85rem }
  triangle-node: { fontSize: 0.9rem }
  grid-header: { fontSize: 0.85rem, fontWeight: 500 }
  grid-cell-result: { fontSize: 0.9rem, fontWeight: 600, selected: 700 }
  text-wrap: "Headings (h1-h6, .h1-.h6) balance; p and li pretty. Set with :where() so specificity stays zero. Web only (theme.css); the PDF and email are unchanged. Progressive enhancement."

rounded:
  card: 0.5rem
  swatch: 0.2rem
  dot-control: 50%

spacing:
  scale: "Bootstrap utilities (0.25rem steps)"
  minimum-target: 44px            # main .btn, form-control-sm, summary, footer links
  minimum-dot-hit-area: "32px (visual 1rem plus transparent ::after inset -0.5rem)"
  intro-max-width: 40rem
  persona-preview-max-width: 44rem
  triangle-max-width: 320px

components:
  option-card: "Native radio or checkbox followed by a label card. State from :checked + sibling, no JS. Selected = accent border, selected-tint fill, weight 600. Focus = 2px accent outline, 2px offset."
  spectrum: "Row of boxes, one per labelled option, plus small round 'mix' dots between options. Dots carry a visually hidden flanking-option label for screen readers."
  triangle: "CSS-drawn triangle, three corner nodes plus three round edge-midpoint nodes. Max width 320px."
  persona-grid: "Static, labelled 3x3 result grid reconstructed from two answers. Selected cell = brand-primary fill, white bold text, tick prefix, soft shadow. Muted cells use muted-border and muted-text."
  relationship-cells: "Ally = solid border, blue. Friend = dashed border, teal. Necessity = dotted border, purple. A persona in more than one category gets a diagonal tint split and the more prominent border style. A legend sits below the grid."
  persona-card: "Hero card: selected-tint background, accent border, inline line-art SVG icon (colour = brand accent; 64px, 56px on phones stacked above the name, 36px in the PDF), larger bold name, eyebrow in header-text, tagline, description. Collapsible 'Now and next / who to work with' section via details/summary, 44px min height."
  result-sections: "Sections below the hero (grid, innovation, share) are borderless with no fill or shadow, 2rem apart. The innovation card keeps its band-colour left border."
  share-actions: "Result share section has one primary action, 'Share on LinkedIn' (btn-success, brand-primary fill, full size). Download PDF, Download certificate, Copy caption (directly under the caption) and Email me a copy are secondary: btn-outline-success remapped to brand-accent text and border, brand-primary fill with white text on hover. btn-sm, 44px min height. No filled grey buttons."
  footer-link: "Footer links use brand-accent and are underlined (colour is never the only cue). 44px min height. Hover/focus darken to brand-primary-dark in light and thicken the underline in dark."
  persona-badge: "Appears in the survey progress area after persona resolution, 300ms reveal animation, disabled under prefers-reduced-motion."
  innovation-card: "Card with 6px left border in band colour (decorative; band also named in text). Band legend with swatches (aria-hidden) beside text names: centred wrapping row on wider screens, equal-column grid on phones."
  charts: "Radar fingerprint and innovation bell-curve are server-rendered SVG (charts.py). Band-name text labels live in HTML, not in the SVG, so they do not shrink with the viewBox. The respondent's bar is full opacity with a 3-unit strong-text outline (#212529 in the SVG, var(--strong-text) on the web so it flips in dark)."
  share-card: "1200x630 PNG (og:image) and 1200x1200 certificate PNG, rendered by cairosvg. Accent = band colour, falling back to #2e7d32."
  pdf: "WeasyPrint render from pdf/result.html."
  email: "Opt-in result copy. Inline styles only, no theme.css."
---

# Monkey Puzzle design system

## Intent

"Know yourself," not "measure what you're doing wrong." The tone is warm, curious and low-pressure. People arrive from a link, answer about 11 short steps on a phone or laptop, and get a persona they will want to show someone. The look should be calm and plain enough that the questions feel easy, with the result page as the one place that is allowed to feel like a reward.

This is a single-brand product. There is no per-client theming. Rob and Andrew retune scoring, band cutoffs, band colours, persona copy and taglines in `content/survey.yaml` without a deploy, so design must work with whatever colours and text they enter.

## Rules

1. **Native controls, no selection JavaScript.** Radios and checkboxes stay real inputs. Selected state comes from `:checked + sibling` CSS. New widgets follow the same pattern (`option-card`, `spectrum-node`, `triangle-node`).
2. **Colour never works alone.** Relationships use border style (solid, dashed, dotted) plus colour. Bands use a text name beside every swatch. Personas use an icon plus name. The selected grid cell uses a tick, fill and weight, not only a colour shift.
3. **Visible focus everywhere.** 2px accent outline with 2px offset on every interactive element, including the hidden-input sibling pattern. Never remove an outline without replacing it.
4. **Targets are generous.** 44px minimum for buttons, small inputs, `summary` and footer links. Small visual controls (the mix dots) get a transparent hit area of about 32px.
5. **Light and dark are first-class.** `base.html` sets `data-bs-theme` from `prefers-color-scheme`. Any new custom surface defines both values in `:root` variables. Don't hardcode `#fff` or `#212529` in components. Re-check Bootstrap components that dark mode leaves low-contrast (as was done for `.btn-outline-secondary`).
6. **One green family, used sparingly.** `brand-primary` is the selected-cell fill and share-card accent; primary buttons use it too; secondary buttons use `brand-accent` outlines. `brand-accent` is the text, border and outline colour and swaps to a lighter green on dark. Relationship colours deliberately avoid green, muted grey and the band ramp so nothing collides.
7. **Motion is optional.** The only motion is the persona badge reveal and a 0.98 press scale (`:active`) on option cards, spectrum and triangle nodes, focusable result-grid cells and buttons. Press feedback lives only inside `@media (prefers-reduced-motion: no-preference)`. The badge reveal is switched off under `reduce`. Animate `transform` and `opacity` only. List transition properties, never `transition: all`.
8. **Results are multi-surface.** A result change is not done until it works on the web page, the PDF, the email copy, the OG share card and the certificate. Inline SVG and email styles do not inherit `theme.css`.
9. **Content is data.** Don't hardcode persona names, taglines, band names, colours or cutoffs in templates or CSS. Design for the longest plausible text (long taglines, nine personas).
10. **Scriptless by default.** CSP blocks inline scripts without the nonce. Prefer HTML and CSS (`details/summary`, `:checked`) over JavaScript.

## Contrast targets

| Pair | Minimum | Current |
|---|---|---|
| Body and label text on surface | 4.5:1 | Pass |
| Muted text on white | 4.5:1 | 4.69:1 (at the floor, do not lighten) |
| White text on `brand-primary` | 4.5:1 | 5.13:1 |
| Accent text or border on dark surface | 4.5:1 text, 3:1 border | 7.67:1 |
| Focus outline, control borders, chart marks vs background | 3:1 | See gaps |
| Relationship colour vs its tint (borders) | 3:1 | Friend teal vs tint is 3.84:1 (text use would fail) |

## Known gaps to fix when touched

- **Band swatches fail 3:1 against white** (WCAG 1.4.11) when used as a graphic: yellow `#f1c40f` is 1.66:1, light green `#7cb342` 2.50:1, amber `#e67e22` 2.85:1. The respondent's highlighted bar now has a dark outline (#0051), so it is visible in every band. The swatches, the band dot, the card's left stripe and the unhighlighted bars still use the raw band colours and still fail 3:1 in the pale bands, always beside a text name. Darker band colours remain Rob and Andrew's call, to propose rather than change.
- **Never put white text on a band colour.** White on yellow is 1.66:1 and on light green 2.50:1. Use dark text on the light bands (black on yellow is 12.64:1).
- **Share card and certificate use the band colour as the accent** (`render_certificate_svg`). Check text contrast on the yellow and light-green bands.
- **Friend teal `#00838f` on its tint is 3.84:1.** Fine for borders, below 4.5:1 for any text in that colour. Keep cell label text in `strong-text`.
- **Laggards tagline** reads "You are a Laggard. Wanker." This is content in `survey.yaml`, so it's Rob and Andrew's call, but it clashes with the "know yourself" framing and will appear on the share card.
- Persona icons are placeholder line art (backlog #0005). A real illustration set would raise the quality of the result page and share card more than any colour change.

## Borrowed from the reference library

The calm, plain-surface-with-one-accent approach of `notion` and `cal`, and the humane form clarity of `wise`. Their palettes, display type and marketing layouts were not adopted. This is a form-and-result product, and the existing system is already more accessible than most of them.

## Using this file

- Read it before editing any template, `theme.css`, `charts.py` colours or the share card.
- Update it in the same change when a token, rule or component changes.
- `/ship` coder and design-review stages read this file when present.
