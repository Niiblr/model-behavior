# Changelog

All notable changes to this project will be documented in this file.

---

## [2026-02-24]

### config.py / council.py

#### Changed
- **Chairman isolation** — The Chairman (DeepSeek V3.1) was participating in the debate it later judges, biasing its final synthesis. It is now excluded from Council Stages 1 & 2 and Hybrid Phases 1 & 2, appearing only to deliver the final answer.
- **Devil's Advocate separation and isolation** — The Chairman was also doubling as the Devil's Advocate, meaning the same model argued against a consensus it then had to synthesize — undermining both roles. The Devil's Advocate is now a dedicated model with its own config, excluded from Hybrid Phases 1 & 2 so it arrives in Phase 3 without prior positions formed during the debate.

- **OpenRouter Rate Limiting** - Free tier OpenRouter models share rate limits across all users. Firing all models simultaneously was reliably triggering 429 errors. 
OpenRouter models are now staggered 3 seconds apart instead of firing in parallel. Non-OpenRouter models (Ollama, Gemini) are unaffected and still fire immediately.
Added retry with exponential backoff (up to 4 attempts, starting at 5s) when a 429 is received. Also added a guard against unexpected response shapes that was causing a silent 'choices' crash.

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