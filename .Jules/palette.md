## 2024-03-14 - Interactive Spans Require Keyboard Support
**Learning:** The dashboard uses `<span>` elements for critical interactive actions like triggering dream cycles (`#dream-state`). While it has a cursor pointer and an `onclick` handler, it lacked keyboard support, effectively locking out screen reader and keyboard-only users from triggering actions.
**Action:** Always verify that interactive elements that are not native `<button>` or `<a>` tags have `role="button"`, `tabindex="0"`, and an `onkeydown` handler to ensure full accessibility.

## 2024-03-14 - Global Focus Visible Missing
**Learning:** The application lacked any visible focus states for keyboard navigation, making it impossible to navigate the UI with a keyboard effectively.
**Action:** Added a global `:focus-visible` rule. In future components, ensure focus states are explicitly handled or rely on the global rule.

## 2024-03-14 - Template Literal Interpolation Bug
**Learning:** When generating HTML strings within template literals (like in JavaScript mapping functions), escaping the `$` character (e.g., `\${var}`) prevents evaluation and renders the literal string for users (e.g., `aria-label="Toggle ${info.label} sensor"`). This is especially detrimental for screen readers.
**Action:** Ensure template variables inside `aria-` attributes are correctly evaluated without escape characters to provide the intended programmatic name.

## 2024-05-01 - Replace non-semantic interactive elements with buttons
**Learning:** Legacy UI components (like `<span onclick="...">` and `<div onclick="...">`) used to simulate buttons fail proper accessibility standards even with `role="button"` and `tabindex="0"`. They cause keyboard navigation problems and disrupt semantic structure.
**Action:** Always replace non-semantic interactive list items or simulated buttons with native `<button type="button">`. When doing so, to preserve the previous visual design and avoid layout regressions, apply an inline CSS reset (`border: none; background: transparent; text-align: left; padding: 0; margin: 0; font-family: inherit; color: inherit; appearance: none;`) *before* any other styles. If replacing a block-level `<div>`, include `width: 100%` in the reset.
