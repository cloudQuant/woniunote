# Experience Design — Theme Selection and Reading Surfaces

## Foundation

WoniuNote is content-first: the reader should always understand where to read, where to act, and what state an action has reached. Theme switching is a preference control, not a visual toy; it must be quick, reversible, understandable, and available without a mouse.

## Information Architecture

The header contains one compact `主题` control. Opening it reveals:

1. A title, count, and current selection.
2. A bright-theme group for daytime and long-form reading.
3. A dark-theme group for night use and focused browsing.
4. Preview cards that show navigation, content surface, text, and action hierarchy together.

No secondary settings page is needed because theme selection is a single, immediate preference.

## Component Behaviour

### Theme trigger

- Native button; it receives tab focus and opens the popover with keyboard activation.
- Hover and open states use the current navigation hover token.
- The accessible label always states the currently selected theme.

### Theme card

- A card shows miniature navigation, page field, raised content, text line, and action color.
- The card carries the theme name, a short reason to choose it, and its bright/dark label.
- The selected card has both a visual border/check indicator and `aria-pressed="true"`.
- Selecting a card applies the theme immediately, persists it, announces the new current selection through a polite live region, and closes the menu.

### Reading and sidebar surfaces

- Shared cards and article rows use one border plus a low theme-specific shadow, preventing light themes from looking washed out and dark themes from merging together.
- Hover raises only interactive article rows; static sidebars keep stable hierarchy.
- The same surface tokens drive Element Plus inputs, overlays, cards, pagination, and buttons.

## States

| Component | Rest | Hover | Active / selected | Keyboard focus | Reduced motion |
| --- | --- | --- | --- | --- | --- |
| Header theme control | Transparent nav background | Nav hover field | Open-state nav field | Offset visible outline + halo | No color transition |
| Theme card | Surface + border | Stronger border, subtle lift | Primary border + check | Offset visible outline + halo | No lift transition |
| Article row | Surface + border + low shadow | Stronger border + elevation | Route navigation handles selection | Offset visible outline + halo | No transform transition |
| Filled action | Semantic background + `on-*` text | Contrast-safe hover token | Contrast-safe active token | Offset visible outline + halo | No animation required |

## Content and Voice

- Use concise Chinese labels in the user interface: `主题`, `明亮主题`, `暗色主题`, and `当前`.
- Describe a theme by the reading/work situation it supports, rather than a vague aesthetic claim.
- Do not rely on color alone for selected, focus, success, warning, or error states.

## Accessibility

- Body and auxiliary text are intentionally tested against their actual CSS surface, including the muted tier.
- The focus marker combines outline, offset, and halo so it remains visible on busy cards and in both palette families.
- Theme cards are buttons, not clickable generic containers.
- Preview art is `aria-hidden`; the adjacent button label contains all meaningful information.

## Key Flow

1. Reader tabs to `主题` in the header.
2. Reader opens the selector and scans bright/dark groups with concise descriptions.
3. Reader chooses a card using mouse, touch, Enter, or Space.
4. WoniuNote changes `data-theme` on `<html>`, adjusts Element Plus dark mode where needed, persists the stable key, and closes the selector.
5. On the next visit, the saved key is applied before visible content renders.
