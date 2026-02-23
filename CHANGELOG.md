# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

---

## [2026-02-23]

### ChatInterface.jsx

#### Added
- **Mode tooltips** — Hovering over the 🏛️ Council or 🔀 Hybrid mode buttons now shows a styled dark tooltip explaining what each mode does and its stages/phases.
- **Mode auto-detection** — When opening an existing conversation, the active mode is now automatically detected from the messages. Hybrid conversations are detected via the `mode` field; Council conversations are inferred from the presence of `stage1/stage2/stage3` data.
- **Mode locking** — Once a conversation has messages, the mode toggle is locked. The inactive button is grayed out and unclickable, with a 🔒 "Mode locked to this conversation" notice displayed next to the buttons. New/empty conversations remain fully unlocked.
- **Per-message mode badge** — Each assistant reply now displays a small colored pill (blue 🏛️ Council or purple 🔀 Hybrid) indicating which mode was used to generate that response.
- **Changelog** — Added changelog.md


#### Fixed
- **Mode lock not working for Council conversations** — Council messages do not store an explicit `mode` field, so detection was falling through. Fixed by inferring `'council'` from the presence of stage data when no `mode` field is found.
- **Wrong mode locked when switching conversations** — The `useEffect` that sets the mode was depending on `conversationId`, causing it to run before the new conversation's messages were loaded. Fixed by switching the dependency to `conversationMode` so it runs only after the correct mode has been resolved from the new messages.