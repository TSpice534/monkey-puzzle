---
version: alpha
name: Monkey-Puzzle-design-system
description: A friendly, calm, single-brand survey and result experience on Bootstrap 5.3 with a custom layer (app/static/css/theme.css). One green brand colour, native HTML/CSS controls with no JavaScript for selection, automatic light and dark appearance, and results designed to be shared (web page, PDF, email, 1200x630 share card, 1200x1200 certificate). Colour is never the only carrier of meaning: relationships use border patterns, bands use text labels, and personas use line-art icons.

# Source of truth is theme.css :root. Persona and band content lives in content/survey.yaml.
colors:
  # Brand
  brand-primary: "#2e7d32"        # Fill: selected grid cell, certificate and share-card accent. White text 5.13:1.
  button-success: "#198754"       # Bootstrap btn-success, used for Begin, Next and other primary buttons (measured in the running app). White text 4.53:1. Not the same green as brand-primary.
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
  persona-card: "Hero card: selected-tint background, accent border, inline line-art SVG icon (colour = brand accent; 64px, 56px on phones stacked above the name, 48px in the PDF), larger bold name, eyebrow in header-text, tagline, description. Collapsible 'Now and next / who to work with' section via details/summary, 44px min height."
  result-sections: "Sections below the hero (grid, innovation, share) are borderless with no fill or shadow, 2rem apart. The innovation card keeps its band-colour left border."
  persona-badge: "Appears in the survey progress area after persona resolution, 300ms reveal animation, disabled under prefers-reduced-motion."
  innovation-card: "Card with 6px left border in band colour. Band legend with swatches (aria-hidden) beside text names."
  charts: "Radar fingerprint and innovation bell-curve are server-rendered SVG (charts.py). Band-name text labels live in HTML, not in the SVG, so they do not shrink with the viewBox."
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
6. **One green family, used sparingly.** `brand-primary` is the selected-cell fill and share-card accent; primary buttons currently use Bootstrap `#198754` (see gaps). `brand-accent` is the text, border and outline colour and swaps to a lighter green on dark. Relationship colours deliberately avoid green, muted grey and the band ramp so nothing collides.
7. **Motion is optional.** Only the persona badge reveal animates. Anything new must respect `prefers-reduced-motion: reduce`.
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

- **Band swatches fail 3:1 against white** (WCAG 1.4.11) when used as a graphic: yellow `#f1c40f` is 1.66:1, light green `#7cb342` 2.50:1, amber `#e67e22` 2.85:1. They always sit beside a text band name, so meaning survives, but the card's 6px left border and the bell-curve bars can be nearly invisible in those bands. Candidate fix: add a dark outline to swatches and bars, or darker band colours. These colours are Rob and Andrew's to retune, so propose rather than change.
- **Never put white text on a band colour.** White on yellow is 1.66:1 and on light green 2.50:1. Use dark text on the light bands (black on yellow is 12.64:1).
- **Share card and certificate use the band colour as the accent** (`render_certificate_svg`). Check text contrast on the yellow and light-green bands.
- **Friend teal `#00838f` on its tint is 3.84:1.** Fine for borders, below 4.5:1 for any text in that colour. Keep cell label text in `strong-text`.
- **Laggards tagline** reads "You are a Laggard. Wanker." This is content in `survey.yaml`, so it's Rob and Andrew's call, but it clashes with the "know yourself" framing and will appear on the share card.
- Persona icons are placeholder line art (backlog #0005). A real illustration set would raise the quality of the result page and share card more than any colour change.

- **Two greens.** Primary buttons render `#198754` (Bootstrap `btn-success`) while the selected cell, icons and share card use `#2e7d32`. Pick one, ideally by overriding `btn-success` or switching buttons to a `--brand-primary` variant.
- **Footer "Email Us" link** is Bootstrap blue `#0d6efd` on `#f8f9fa`, 4.26:1, fails AA (axe-core, measured in the running app). It is also the only blue on the site.
- **Secondary actions look disabled.** All result-page share actions are grey outline buttons, and "Email me a copy" is a filled grey `btn-secondary`. There is no primary action on the page whose purpose is sharing.

## Borrowed from the reference library

The calm, plain-surface-with-one-accent approach of `notion` and `cal`, and the humane form clarity of `wise`. Their palettes, display type and marketing layouts were not adopted. This is a form-and-result product, and the existing system is already more accessible than most of them.

## Using this file

- Read it before editing any template, `theme.css`, `charts.py` colours or the share card.
- Update it in the same change when a token, rule or component changes.
- `/ship` coder and design-review stages read this file when present.
