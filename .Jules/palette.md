## 2024-03-14 - Interactive Spans Require Keyboard Support
**Learning:** The dashboard uses `<span>` elements for critical interactive actions like triggering dream cycles (`#dream-state`). While it has a cursor pointer and an `onclick` handler, it lacked keyboard support, effectively locking out screen reader and keyboard-only users from triggering actions.
**Action:** Always verify that interactive elements that are not native `<button>` or `<a>` tags have `role="button"`, `tabindex="0"`, and an `onkeydown` handler to ensure full accessibility.

## 2024-03-14 - Global Focus Visible Missing
**Learning:** The application lacked any visible focus states for keyboard navigation, making it impossible to navigate the UI with a keyboard effectively.
**Action:** Added a global `:focus-visible` rule. In future components, ensure focus states are explicitly handled or rely on the global rule.

## 2024-03-14 - Template Literal Interpolation Bug
**Learning:** When generating HTML strings within template literals (like in JavaScript mapping functions), escaping the `$` character (e.g., `\${var}`) prevents evaluation and renders the literal string for users (e.g., `aria-label="Toggle ${info.label} sensor"`). This is especially detrimental for screen readers.
**Action:** Ensure template variables inside `aria-` attributes are correctly evaluated without escape characters to provide the intended programmatic name.

## 2024-04-03 - Prefer Semantic Buttons Over ARIA Roles for Accessibility
**Learning:** Some interactive list elements and triggers in the UI (`#dream-state`, `.api-ep-item`, and history items) were built using `<div>` or `<span>` tags with `onclick` handlers, occasionally combined with manual `role="button"` and keydown event listeners. This approach often introduces accessibility gaps (like missing spacebar activation or unreliable focus ring application) and bloats the HTML.
**Action:** Always prefer native semantic `<button type="button">` elements for interactive actions instead of retrofitting `<div>` or `<span>` elements. Use CSS reset styles (`border: none; background: transparent; appearance: none;` etc.) to maintain the visual design while inheriting full, native keyboard navigation and screen reader support for free.
