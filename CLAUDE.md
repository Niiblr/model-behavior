# CLAUDE.md - Technical Notes for Model Behavior by Niiblr

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

Model Behavior by Niiblr is a multi-stage deliberation system where multiple LLMs collaboratively answer user questions. The system supports two modes:

- **Council Mode** (original): 3-stage process — individual responses, peer rankings, chairman synthesis
- **Hybrid Mode** (new): 4-phase process — Socratic, Debate, Devil's Advocate, Chairman Synthesis

The key innovation in Council mode is anonymized peer review in Stage 2, preventing models from playing favorites. The key innovation in Hybrid mode is sequential phases that build on each other, forcing genuine engagement between models.

---

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` list — each entry has `provider`, `model`, and `name` keys
- Contains `CHAIRMAN_CONFIG` dict — same structure as a council model entry
- Supports multiple providers: OpenRouter, Ollama (local and cloud), Google Gemini, OpenAI
- Uses `.env` file for API keys: `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_CLOUD_API_KEY`
- Backend runs on **port 8001** (NOT 8000 — user had another app on 8000)
- Providers are instantiated at module load; `None` providers are filtered out of `COUNCIL_MODELS`

**`providers/`**
- Multi-provider system replacing original single OpenRouter provider
- `openrouter.py`, `ollama.py`, `gemini.py`, `openai.py` — each implements `query_model()` and `query_models_parallel()`
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with `content` key; graceful degradation — returns `None` on failure

**`council.py`** — The Core Logic

*Original Council Mode functions:*
- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_collect_rankings()`: Anonymizes responses as "Response A, B, C..." then parallel ranking queries; returns tuple `(rankings_list, label_to_model_dict)`
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section
- `calculate_aggregate_rankings()`: Computes average rank position across peer evaluations
- `run_full_council()`: Orchestrates all three stages
- `generate_conversation_title()`: Uses chairman model to generate 3-5 word title

*Hybrid Mode functions (added):*
- `hybrid_phase1_socratic()`: Calls `stage1_collect_responses()` — initial answers
- `hybrid_phase2_debate()`: Each model reads all Phase 1 responses and agrees/disagrees/adds nuance
- `hybrid_phase3_devils_advocate()`: Chairman argues against the emerging consensus
- `hybrid_phase4_synthesis()`: Chairman delivers final answer having seen all phases
- `_build_responses_text()`: Helper that formats model responses into readable text blocks
- `run_hybrid_council()`: Orchestrates all four phases

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, title, messages[]}`
- Council assistant messages: `{role, stage1, stage2, stage3, metadata}`
- Hybrid assistant messages: `{role, mode: "hybrid", hybrid_phase1, hybrid_phase2, hybrid_phase3, hybrid_phase4, stage1: [], stage2: [], stage3: null, metadata: {mode: "hybrid"}}`
- Note: Council metadata (label_to_model, aggregate_rankings) is NOT persisted — only returned via API and held in frontend state

**`main.py`**
- FastAPI app with CORS enabled for `localhost:5173` and `localhost:3000`
- `SendMessageRequest` includes a `mode` field (default: `"council"`)

*Endpoints:*
- `POST /api/conversations/{id}/message` — non-streaming council (legacy)
- `POST /api/conversations/{id}/message/stream` — streaming council mode (SSE)
- `POST /api/conversations/{id}/message/stream/hybrid` — streaming hybrid mode (SSE)
- `GET /api/conversations/{id}/export` — markdown export (handles both modes)
- `GET /api/conversations/{id}/export/html` — HTML export (handles both modes)
- `DELETE /api/conversations/{id}/messages` — clear messages
- `DELETE /api/conversations/{id}` — delete conversation
- `PUT /api/conversations/{id}/title` — rename conversation

*Streaming events — Council mode:*
`stage1_start` → `stage1_complete` → `stage2_start` → `stage2_complete` → `stage3_start` → `stage3_complete` → `title_complete` → `complete`

*Streaming events — Hybrid mode:*
`hybrid_phase1_start` → `hybrid_phase1_complete` → `hybrid_phase2_start` → `hybrid_phase2_complete` → `hybrid_phase3_start` → `hybrid_phase3_complete` → `hybrid_phase4_start` → `hybrid_phase4_complete` → `title_complete` → `complete`

*Export logic:*
- Both export endpoints check `message.get("mode") == "hybrid"` to branch between council and hybrid rendering
- Council MD export: Stage 1, Stage 2, Stage 3 sections
- Hybrid MD export: Phase 1 through Phase 4 sections
- HTML export renders both modes with tabbed interfaces; hybrid gets a dark purple header bar
- Title escaping includes `&`, `"`, `<`, `>`, and `'` (as `&#39;`) to prevent broken HTML
- "Devil's Advocate" is written as "Devils Advocate" in JS string literals inside the HTML template to avoid apostrophe syntax errors

---

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Manages conversations list and current conversation state
- `handleSendMessage(content, mode)` — accepts mode parameter, routes to correct endpoint
- Placeholder assistant message on send includes both council fields (`stage1`, `stage2`, `stage3`) and hybrid fields (`hybrid_phase1`, `hybrid_phase2`, `hybrid_phase3`, `hybrid_phase4`) and `mode`
- Handles all streaming events for both modes and updates UI as each phase/stage completes
- Tracks `hybridLoadingPhase` state and passes it down to `ChatInterface` as a prop

**`components/ChatInterface.jsx`**
- Accepts `hybridLoadingPhase` prop from `App.jsx` (phase tracking lives in App, not here)
- Mode selector UI: two pill buttons (🏛️ Council / 🔀 Hybrid) above the textarea
- `handleSubmit` passes `mode` to `onSendMessage`
- `getLoadingMessage()` returns contextual funny/dramatic messages per phase:
  - Phase 1: "Your question has been submitted to the Council for consideration..."
  - Phase 2: "Council members confirm they received each other's answers and the debate has begun..."
  - Phase 3: "A Devil's Advocate has entered the chamber..."
  - Phase 4: "The Chairman has called for order..."
- Message rendering checks `message.mode === 'hybrid'` to show `<HybridView>` vs original stage components

**`components/HybridView.jsx`** *(new file)*
- Renders all 4 hybrid phases
- Dark purple gradient header bar identifying hybrid mode
- Each phase is a collapsible panel (click header to expand/collapse)
- Phases 1 and 2 (multi-model) use tabbed interface per model
- Phases 3 and 4 (single model) render directly
- Shows loading spinner inside a phase panel while it's in progress

**`components/HybridView.css`** *(new file)*
- Styles for hybrid view panels, tabs, spinner, header
- Phase 1: blue tones; Phase 2: amber tones; Phase 3: red tones; Phase 4: green tones

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering

**`components/Stage2.jsx`**
- Tab view showing raw evaluation text from each model
- De-anonymization happens client-side
- Shows "Extracted Ranking" below each evaluation
- Aggregate rankings shown with average position and vote count

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background to highlight conclusion

---

## Key Design Decisions

### Hybrid Mode Phase Design
- **Phase 1 (Socratic)** reuses `stage1_collect_responses()` — no duplication
- **Phase 2 (Debate)** explicitly instructs models they are *allowed to strongly disagree* — without this, models tend toward agreeable non-answers
- **Phase 3 (Devil's Advocate)** uses the Chairman model specifically so it has the authority and context to challenge effectively
- **Phase 4 (Synthesis)** passes all three prior phases in full so Chairman has complete context
- Each phase prompt includes the full text of previous phases — context grows with each step

### Mode Selector Placement
- Mode selector sits above the textarea, not in the header — it's part of the compose action
- Mode persists within a conversation session but resets on page reload
- Old conversations without a `mode` field default to council rendering automatically

### Export Safety
- All user-generated text passed into HTML is run through `escHtml()` in JavaScript
- Python-side title escaping covers `&`, `"`, `<`, `>`, `'`
- Apostrophes in JavaScript string literals inside the f-string HTML template must be avoided — use "Devils Advocate" not "Devil's Advocate" in those contexts

### Stage 2 Prompt Format (Council Mode)
Strict format requirements for reliable parsing:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header (all caps, with colon)
3. Numbered list: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

### De-anonymization Strategy (Council Mode)
- Models receive anonymous labels: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "Gemini 3.0 Flash", ...}`
- Frontend displays model names in bold for readability
- Prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to a single model failure
- `None` responses are filtered out before processing

---

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`). Run backend as `python -m backend.main` from project root.

### Port Configuration
- Backend: **8001**
- Frontend: **5173** (Vite default)

### File Locations
All component files live in `frontend/src/components/` — this includes `HybridView.jsx` and `HybridView.css`. Placing them in the wrong folder causes "X is not defined" React errors even if the import line is present.

### Hybrid Message Storage
Hybrid messages intentionally include empty council fields (`stage1: [], stage2: [], stage3: null`) so that old code paths that expect these fields don't crash on hybrid messages.

### Markdown Rendering
All ReactMarkdown components should be wrapped in `<div className="markdown-content">` for proper spacing (defined in `index.css`).

---

## Common Gotchas

1. **"X is not defined" React error** — almost always a missing import line at the top of the file, or the component file is in the wrong folder
2. **White screen** — JavaScript crash; check browser console (F12) for the exact error
3. **Hybrid results not appearing** — streaming event handlers missing in `App.jsx`; check that all four `hybrid_phaseX_complete` handlers are present
4. **HTML export blank** — apostrophe in a JavaScript string literal inside the Python f-string template breaks the script; avoid `'` in any hardcoded JS strings in the template
5. **Module Import Errors** — always run backend as `python -m backend.main` from project root
6. **CORS Issues** — frontend origin must match allowed origins in `main.py` CORS middleware
7. **Config changes not taking effect** — must restart the backend; Python doesn't hot-reload config

---

## Performance Notes

- Hybrid mode takes approximately 2-3x longer than Council mode
- Phase 2 and beyond have much longer prompts (include all previous phases)
- Current models are Ollama cloud (`:cloud` suffix) — RAM is not a concern
- For truly local models: 7B-13B is fine for hybrid; 70B+ needs 40GB+ RAM
- To speed up testing: temporarily comment out all but one model in `config.py`, restart backend

---

## Data Flow Summary

### Council Mode
```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation
    ↓
Stage 3: Chairman synthesis
    ↓
Stream to frontend: stage1_complete → stage2_complete → stage3_complete → complete
```

### Hybrid Mode
```
User Query
    ↓
Phase 1 (Socratic): Parallel initial answers
    ↓
Phase 2 (Debate): Each model reads Phase 1, agrees/disagrees/adds nuance — parallel
    ↓
Phase 3 (Devil's Advocate): Chairman challenges the emerging consensus — single model
    ↓
Phase 4 (Synthesis): Chairman delivers final answer with full context — single model
    ↓
Stream to frontend: hybrid_phase1_complete → hybrid_phase2_complete → hybrid_phase3_complete → hybrid_phase4_complete → complete
```

---

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Share conversations via public URL (ngrok + read-only `/share/{id}` endpoint)
- Timeout per model in Phase 1/2 so slow models don't block the whole phase
- Dynamic rounds mode: conversation continues until consensus reached
- Export hybrid conversations with better visual differentiation in HTML
- Model performance analytics over time
- Custom ranking criteria for Stage 2
- Support for reasoning models with special handling