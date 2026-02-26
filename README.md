# Model Behavior
### by Niiblr

![header](https://raw.githubusercontent.com/Niiblr/model-behavior/master/header.jpg)

> *Multiple AIs walk into a room.*

Most AI tools give you one model, one answer. Model Behavior takes a different approach: it assembles a council of multiple LLMs and puts them through a structured debate. 
You can run the **original Council mode** — [Karpathy's](https://github.com/karpathy/llm-council) classic 3-stage process of independent answers, peer ranking, and synthesis or tou can run the **New Hybrid mode**, which adds a full debate phase and a dedicated devil's advocate that challenges whatever consensus is emerging before the chairman delivers the final result. The goal is a more pressure-tested answer than any single model could produce on its own.

---

## What's New vs the Original

| Feature | karpathy/llm-council | Model Behavior |
|---|---|---|
| Providers | OpenRouter only | OpenRouter, Ollama (local + cloud), Gemini, OpenAI |
| Response mode | Wait for everything | Streaming — results appear phase by phase |
| Council mode | 3-stage (original) | ✅ Preserved with minor UI changes |
| Hybrid mode | ❌ | ✅ 4-phase: Socratic → Debate → Devil's Advocate → Synthesis |
| Export | ❌ | ✅ Markdown and HTML (both modes) |
| UI | ✅ | ✅ Improved UI for readibility and clarity |

---

## Two Modes

### 🏛️ Council Mode (original)
The classic Karpathy 3-stage process:
1. **Stage 1** — All models answer independently
2. **Stage 2** — Models review and rank each other's answers anonymously
3. **Stage 3** — Chairman synthesizes the final answer

### 🔀 Hybrid Mode (new)
A more conversational 4-phase process inspired by how humans actually debate:
1. **Phase 1 (Socratic)** — All models form their initial understanding
2. **Phase 2 (Debate)** — Each model reads the others' answers and agrees, disagrees, or adds nuance
3. **Phase 3 (Devil's Advocate)** — One model challenges the emerging consensus head-on
4. **Phase 4 (Synthesis)** — The Chairman delivers a final answer informed by the full debate

→ [See the UI in action](ui-preview.png)

---

## Setup

### 1. Install Dependencies

**Backend:**
```
uv sync
```

**Frontend:**
```
cd frontend
npm install
cd ..
```

### 2. Configure API Keys

Create a `.env` file in the project root and add whichever keys you have:

```
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=...
OLLAMA_CLOUD_API_KEY=...
```

You only need keys for the providers you intend to use.

## Flexible Model Mixing

One of the most powerful features of Model Behavior is that you can mix any 
combination of providers in the same council simultaneously:

- **Cloud models via OpenRouter** — single API key, access to GPT, Claude, Gemini, Grok and more
- **Direct API keys** — connect to Google Gemini, OpenAI, or others directly without OpenRouter
- **Ollama cloud models** — large models running on Ollama's cloud servers
- **Ollama local models** — models running entirely on your own machine, free and private

A council of a local Llama 3 on your PC, a cloud Gemini via direct API, 
and a GPT model via OpenRouter all debating the same question is completely valid.

### Setting up local models with Ollama

1. Download and install Ollama from https://ollama.com
2. Pull any model you want:
```
   ollama pull llama3
   ollama pull mistral
   ollama pull gemma3
```
3. Add them to your council in `backend/config.py`:
```python
   {
       "provider": ollama_local,
       "model": "llama3",
       "name": "Llama 3 (Local)"
   }
```

### RAM requirements for local models

| Model size | Minimum RAM |
|---|---|
| 7B | 8GB |
| 13B | 16GB |
| 34B | 32GB |
| 70B+ | 64GB+ Not recommended|

Local models are slower but completely private — nothing leaves your machine.

### 3. Configure Models

Edit `backend/config.py` to set up your council. Each model needs a `provider`, `model`, and `name`:

```python
COUNCIL_MODELS = [
    {
        "provider": gemini,
        "model": "gemini-3-flash-preview",
        "name": "Gemini 3.0 Flash"
    },
    {
        "provider": openrouter,
        "model": "openai/gpt-5.1",
        "name": "GPT-5.1"
    },
]

CHAIRMAN_CONFIG = {
    "provider": gemini,
    "model": "gemini-3-pro-preview",
    "name": "Chairman Gemini"
}
```

---

## Running the App

**Terminal 1 — Backend:**
```
cd backend
uv run python -m backend.main
```

**Terminal 2 — Frontend:**
```
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---
## Staying Up to Date
Run this to get the latest version:
```
git pull origin main
```

## Changelog
Consult changes [here](CHANGELOG.md)

## Tech Stack

- **Backend:** FastAPI (Python), async, multi-provider LLM support
- **Frontend:** React + Vite, streaming SSE, ReactMarkdown
- **Storage:** JSON files in `data/conversations/`
- **Package management:** uv (Python), npm (JavaScript)

---

## Credits

Based on [karpathy/llm-council](https://github.com/karpathy/llm-council) by Andrej Karpathy, who built the original 3-stage council concept and explicitly invited the community to take it further. This is Niiblr's attempt at doing exactly that.

*Niiblr is a personal handle. Unlikely affiliation with the Futurama character.*
