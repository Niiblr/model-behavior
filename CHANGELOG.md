# Changelog

All notable changes to this project will be documented in this file.

---

## [2026-03-10]

### backend/main.py | frontend/src/components/ChatInterface.jsx | frontend/src/components/ChatInterface.css

#### Added
- **📎 File upload — send documents to the Council** — Users can now attach a file to any council query. A paperclip button (📎) sits to the left of the textarea and opens a browser file picker. Supported formats: **pdf, docx, txt, sh, py, md, xls, xlsx**.
  - *Backend:* new `POST /api/upload` endpoint in `main.py` extracts plain text from the uploaded file using `pypdf` (PDF), `python-docx` (Word), `openpyxl`/`xlrd` (spreadsheets), or UTF-8 decode (text/code/markdown). Returns `{ text, filename, size }`. Max file size: 20 MB.
  - *Frontend:* the extracted text is prepended to the user's typed message before it is sent to the council, so every model in the council — in both **Council** and **Debate** modes — receives the full file content as context with no changes to the orchestration logic.
  - *UI:* after a file is picked, a removable **file chip** appears below the textarea showing the filename. The submit button becomes enabled once a file is attached (even without typed text). Sent messages show a small **📄 filename badge** above the user's question.
- **`python-multipart` dependency** — Added to support FastAPI multipart file uploads.

---



### council.py | main.py | ChatInterface.jsx | HybridView.jsx | /providers/__init__.py | /providers/openai.py | /providers/gemini.py | /providers/ollama.py | /providers/openrouter.py

#### Renamed
- **Hybrid Mode → Debate Mode** — The second mode has been renamed from "Hybrid" to "Debate" across all user-facing surfaces: mode toggle button, per-message badge, hover tooltip, phase header in `HybridView.jsx`, loading messages, and the Markdown/HTML export headers. The internal API mode key and data field names (e.g. `mode: "hybrid"`, `hybrid_phase1…4`) remain unchanged to preserve backward compatibility with existing stored conversations.

#### Changed
- **Token optimization — parsed rankings to Chairman** — Stage 3 synthesis (`stage3_synthesize_final`) now sends only the structured parsed rankings (e.g., `"Gemini 3 Flash: Response C, Response A, Response B"`) instead of the full verbose evaluation essay from each ranker. Massive token reduction on every council run.
- **Token optimization — dropped Phase 1 from Phase 4 synthesis** — `hybrid_phase4_synthesis` no longer sends the full Phase 1 (Socratic) text, since Phase 2 (Debate) responses already reference and engage with Phase 1 content.
- **Restored Phase 1 to Devil's Advocate (Phase 3)** — Initially removed Phase 1 from `hybrid_phase3_devils_advocate` as a token optimization, but reverted after testing showed the Devil's Advocate produces stronger counterarguments when it can directly reference raw initial positions rather than just the debate meta-commentary.
- **Shortened ranking prompt example** — The Stage 2 ranking prompt's multi-line verbatim example block was compressed from a full mock analysis to `[your analysis here]` followed by the ranking format. Saves tokens on every ranker call × every council member.
- **Title generation uses a cheaper model** — `generate_conversation_title` now defaults to `gemini-flash-latest` (or a small OpenRouter model as fallback) instead of the Chairman (DeepSeek V3.1 671B). A 3–5 word title doesn't need a 671B model.
- **Condensed Chairman preamble** — The chairman synthesis system prompt was made more concise without losing instruction clarity.

#### Added
- **`max_tokens` support across all providers** — The base `Provider` class, `query_model`, `_staggered_query`, and `query_models_parallel` now accept an optional `max_tokens` parameter, passed through to each provider's API in the correct format (OpenAI: `max_completion_tokens`, Gemini: `maxOutputTokens`, Ollama: `options.num_predict`, OpenRouter: `max_tokens`).
- **Per-stage token limits** — Stage 1 / Phase 1 / Phase 2 answers: 4096 tokens. Stage 2 rankings: 1500 tokens. Stage 3: 4096 tokens. Phase 4 synthesis / Devil's Advocate: Uncapped. Title generation: 100 tokens.
- **Whitespace trimming** — All response collection points now `.strip()` model outputs before embedding them into later prompts, removing excess blank lines at zero semantic cost.
- **📡 Model ping/test button** — New "Test Models" button in the sidebar opens a modal that sends a minimal prompt to all configured LLMs. Results stream in live via SSE as each model responds, showing ✅/❌ status and latency in ms. No `max_tokens` cap is applied — models just need to reply something within 120 seconds. Backend: `GET /api/ping` SSE endpoint in `main.py`. Frontend: new `PingModal` component.
- **Gemini safe response parsing** — Fixed a crash (`KeyError: 'parts'`) in `providers/gemini.py` when Gemini returns a response with no `parts` (e.g. safety filter or thinking-model token exhaustion). Now uses safe `.get()` access and logs the full raw response for debugging.
- **Disabled Hermes 3 405B** — Commented out `nousresearch/hermes-3-llama-3.1-405b:free` in `config.py` after OpenRouter returned 402 Payment Required (free tier credits exhausted for that model).

---

## [2026-02-24]

### config.py | council.py | /providers/openrouter.py | /providers/__init__.py

#### Changed
- **Chairman isolation** — The Chairman was participating in the debate it later judges, biasing its final synthesis. It is now excluded from Council Stages 1 & 2 and Hybrid Phases 1 & 2, appearing only to deliver the final answer.
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