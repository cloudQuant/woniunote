---
title: WoniuNote Nine-Theme Design System Refresh
version: 1.0
status: implemented
ui_system: Vue 3, Element Plus, CSS custom properties
colors:
  light_canvas: "#fcf8f3"
  dark_canvas: "#0d0e12"
  action_primary: "#ae563d"
  action_success: "#1e7a46"
  action_warning: "#8a5200"
  action_error: "#b42318"
  action_info: "#2457c5"
typography:
  body: "Inter, PingFang SC, Microsoft YaHei, system sans"
  editorial_display: "Cormorant Garamond, Georgia, Songti SC, serif"
spacing:
  base: "4px"
radius:
  compact: "5px-8px"
  standard: "10px-16px"
  expressive: "18px-26px"
---

# WoniuNote Nine-Theme Design System Refresh

## Intent

Give all nine saved themes a coherent, production-ready design contract rather than treating them as isolated color swaps. Every choice must make reading, scanning, editing, and theme selection clearer while preserving the existing public keys and selected-theme persistence.

## Design Principles

1. **Semantic before decorative.** Components consume `--wn-*` role tokens; colors are never coupled directly to a particular theme name.
2. **Readable at rest and during interaction.** Body, metadata, links, primary controls, feedback controls, and keyboard focus have explicit contrast gates.
3. **Tone has more than color.** Canvas temperature, surface depth, border weight, radius, shadow, typography, and navigation contrast differentiate a theme.
4. **Themes remain comparable.** The same component state has the same semantic meaning in every theme.
5. **Choice is informed.** The selector shows a miniature navigation/content/action hierarchy instead of anonymous color dots.

## Theme Families

| Theme | Family | Intended atmosphere | Surface and shape language |
| --- | --- | --- | --- |
| Claude 暖调 | Editorial light | Long-form, warm and calm | Cream paper, coral action, serif display, soft rounded cards |
| Notion 简约 | Workspace light | Dense, neutral productivity | White canvas, restrained indigo, light borders |
| Vercel 黑白 | Minimal light | Crisp and technical | Graphite monochrome, tight geometry, restrained shadow |
| Stripe 靛蓝 | Fintech light | Clear, polished, confident | Cool canvas, indigo action, generous soft elevation |
| Starbucks 大地绿 | Organic light | Welcoming, tactile reading | Paper canvas, deep green action, expressive rounded cards |
| Linear 深邃 | Focus dark | Precise, low-distraction work | Deep graphite, lavender focus, hairline highlights |
| Spotify 暗夜 | Immersive dark | Comfortable browsing and media | Warm black, vibrant green action, largest radii |
| Supabase 翡翠 | Code dark | Technical clarity | Green-black surfaces, compact geometry, crisp separators |
| Sentry 暗紫 | Data dark | Instrumented, information-rich work | Midnight violet, bright links, layered depth |

## Token Contract

### Core roles

- `--wn-color-canvas`: the page field behind content.
- `--wn-color-surface`, `--wn-color-surface-soft`, `--wn-color-surface-2`: readable elevation steps.
- `--wn-color-text`, `--wn-color-text-secondary`, `--wn-color-text-muted`: text hierarchy; all are readable normal text, not decorative low-contrast text.
- `--wn-color-border`, `--wn-color-border-strong`: stable separation at rest and on hover.
- `--wn-color-link`, `--wn-color-link-hover`: textual navigation independent of the primary action color.

### Action roles

- Primary actions use `primary`, `primary-hover`, `primary-active`, and `on-primary`.
- Feedback actions use `success`, `warning`, `error`, and `info`, each with an explicit `on-*` foreground.
- Filled Element Plus buttons consume the `on-*` tokens at default, hover, and active states. Plain, text, and link buttons keep their outline treatment.

### Interaction roles

- `--wn-color-focus` and `--wn-focus-ring` create a 2px visible outline with an offset halo.
- Cards have a border and a theme-specific shadow; hover increases elevation and border definition without changing layout.
- Reduced-motion preferences remove theme-selector motion and keep the selected state visible.

## Accessibility Requirements

- Normal text, secondary text, muted text, and links on their surface meet **4.5:1**.
- Filled primary and feedback action foreground/background pairs meet **4.5:1** for default, hover, and active primary states.
- Keyboard focus color meets **3:1** against the surface and is rendered with a visible outline plus halo.
- The theme trigger is a native button with `aria-haspopup="dialog"` and `aria-expanded`.
- Every theme card exposes its light/dark mode, description, and selected state through `aria-label` and `aria-pressed`.

## Implementation Map

- `frontend/src/assets/themes/tokens.css` defines the shared contract and Element Plus mappings.
- `frontend/src/assets/themes/*.css` supplies each family’s tokens.
- `frontend/src/assets/main.css` applies border, elevation, and keyboard-focus rules to shared surfaces.
- `frontend/src/config/themes.js` supplies selector metadata and miniature-preview inputs.
- `frontend/src/components/common/ThemeSwitcher.vue` provides the grouped selector interface.

## Validation

- The contrast property test parses the real CSS files so test values cannot drift from the shipped themes.
- Unit tests confirm theme grouping, semantic selected state, and keyboard-capable trigger markup.
- End-to-end testing selects all nine themes, validates the `<html>` theme and dark-mode state, and verifies persistence after reload.
