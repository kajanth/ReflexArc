## 2024-03-14 - Interactive Spans Require Keyboard Support
**Learning:** The dashboard uses `<span>` elements for critical interactive actions like triggering dream cycles (`#dream-state`). While it has a cursor pointer and an `onclick` handler, it lacked keyboard support, effectively locking out screen reader and keyboard-only users from triggering actions.
**Action:** Always verify that interactive elements that are not native `<button>` or `<a>` tags have `role="button"`, `tabindex="0"`, and an `onkeydown` handler to ensure full accessibility.

## 2024-03-14 - Global Focus Visible Missing
**Learning:** The application lacked any visible focus states for keyboard navigation, making it impossible to navigate the UI with a keyboard effectively.
**Action:** Added a global `:focus-visible` rule. In future components, ensure focus states are explicitly handled or rely on the global rule.

## 2024-03-14 - Template Literal Interpolation Bug
**Learning:** When generating HTML strings within template literals (like in JavaScript mapping functions), escaping the `$` character (e.g., `\${var}`) prevents evaluation and renders the literal string for users (e.g., `aria-label="Toggle ${info.label} sensor"`). This is especially detrimental for screen readers.
**Action:** Ensure template variables inside `aria-` attributes are correctly evaluated without escape characters to provide the intended programmatic name.

## 2024-03-24 - Divs and Spans Used as Buttons
**Learning:** In the static dashboard, elements like `.api-ep-item` and `#dream-state` were originally `<div>` or `<span>` elements with `onclick` handlers, relying on custom attributes (`role="button"`, `tabindex="0"`, `onkeydown`) to mimic buttons. This is error-prone and often misses native focus, keyboard, and screen reader behaviors.
**Action:** Instead of adding ARIA attributes and keyboard handlers to non-interactive elements, refactor them into semantic `<button type="button">` tags. Apply CSS resets (e.g., `border: none; background: transparent; appearance: none;`) to maintain visual design while inheriting native accessibility benefits.
