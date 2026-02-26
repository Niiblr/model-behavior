# Model Behavior
### by Niiblr

![header](https://raw.githubusercontent.com/Niiblr/model-behavior/master/header.jpg)

> *Multiple AIs walk into a room.*

Most AI tools give you one model, one answer. Model Behavior takes a different approach: it assembles a council of multiple LLMs and puts them through a structured debate. 
You can run the **original Council mode** — [Karpathy's](https://github.com/karpathy/llm-council) classic 3-stage process of independent answers, peer ranking, and synthesis or tou can run the **New Hybrid mode**, which adds a full debate phase and a dedicated devil's advocate that challenges whatever consensus is emerging before the chairman delivers the final result. The goal is a more pressure-tested answer than any single model could produce on its own.

---

## What's New vs the Original

### 🔌 Providers & Model Support

| Feature | karpathy/llm-council | Model Behavior |
|---|---|---|
| Providers | OpenRouter only | OpenRouter, Ollama (local + cloud), Gemini, OpenAI |
| Response mode | Wait for everything | Streaming — results appear phase by phase |
| Local / offline models | ❌ | ✅ Via Ollama — runs on your own PC, fully private |
| Mix providers in one council | ❌ | ✅ e.g. local Llama + cloud Gemini + GPT via OpenRouter simultaneously |
| Model config format | Simple list of model name strings | Objects with `provider`, `model`, and `name` per entry |
| API keys needed | `OPENROUTER_API_KEY` only | One or more of: OpenRouter, Google, OpenAI, Ollama |

### ⚙️ Process & Modes

| Feature | karpathy/llm-council | Model Behavior |
|---|---|---|
| Council mode (3-stage) | ✅ Original | ✅ Preserved with minor UI changes |
| Hybrid mode (4-phase) | ❌ | ✅ Socratic → Debate → Devil's Advocate → Synthesis |
| Anonymous peer review | ✅ Model identities hidden during ranking | ✅ Preserved from original |
| Response delivery | Wait for all responses | Streaming — results appear phase by phase |
| UI | ✅ | ✅ Improved UI for readability and clarity |

### 💾 Export & Data

| Feature | karpathy/llm-council | Model Behavior |
|---|---|---|
| Export results | ❌ | ✅ Markdown and HTML (both modes) |

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

> **Windows users — new to this?** Follow every step in order. Don't skip any section, even if it looks optional.

---

### Step 0 — Install the required tools

You need four tools installed before anything else. Install them in this order:

**1. Git** (used to download the project)
- Go to https://git-scm.com/download/win
- Download the installer and run it. Click **Next** through all the screens — the defaults are fine.

**2. Node.js** (used to run the frontend)
- Go to https://nodejs.org
- Download the **LTS** version (the one labelled "Recommended For Most Users") and run the installer. Defaults are fine.

**3. Python** (required by the backend)
- Go to https://www.python.org/downloads/
- Download the latest version and run the installer.
- ⚠️ On the very first screen, check the box that says **"Add Python to PATH"** before clicking Install. If you miss this, things won't work.

**4. uv** (a Python tool that manages the backend's packages)
- Open the Windows search bar, type `powershell`, and open **Windows PowerShell**.
- Paste this command and press Enter:
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
- Close PowerShell once it finishes.

---

### Step 1 — Download the project

1. Decide where you want to keep the project. A simple place is your **Documents** folder.
2. Open **Windows PowerShell** again (search for it in the Start menu).
3. Navigate to your Documents folder by typing this and pressing Enter:
```
cd ~/Documents
```
4. Now download the project by running:
```
git clone https://github.com/Niiblr/model-behavior.git
```
This creates a new folder called `model-behavior` inside your Documents folder. That folder is your **project root** — it's where everything lives.

5. Move into that folder:
```
cd model-behavior
```
> Keep this PowerShell window open — you'll need it for the next steps.

---

### Step 2 — Install dependencies

The project has two parts: a **backend** (the Python engine) and a **frontend** (the visual interface in your browser). Each needs its own packages installed.

**Backend** — run this from inside the `model-behavior` folder:
```
uv sync
```

**Frontend** — run these three commands one at a time, pressing Enter after each:
```
cd frontend
npm install
cd ..
```
The last `cd ..` brings you back to the `model-behavior` root folder.

---

### Step 3 — Configure your API keys

API keys are passwords that let the app talk to AI providers like OpenAI or Google. You need at least one.

1. Inside the `model-behavior` folder, find the file called `.env.example`.
2. Make a copy of it and rename the copy to `.env` (no `.example` at the end).
   - In File Explorer: right-click → Copy, then right-click → Paste, then rename it.
   - ⚠️ Make sure it's named exactly `.env` — not `.env.txt` or anything else.
3. Open `.env` with Notepad and fill in the keys for the providers you want to use:

```
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=...
OLLAMA_CLOUD_API_KEY=...
```

You only need keys for the providers you intend to use — leave the others blank or delete those lines.

> Not sure where to get keys? OpenRouter is the easiest starting point — sign up at https://openrouter.ai and you can access many models with a single key.

## Flexible Model Mixing

One of the most powerful features of Model Behavior is that you can mix any 
combination of providers in the same council simultaneously:

- **Cloud models via OpenRouter** — single API key, access to GPT, Claude, Gemini, Grok and more
- **Direct API keys** — connect to Google Gemini, OpenAI, or others directly without OpenRouter
- **Ollama cloud models** — large models running on Ollama's cloud servers
- **Ollama local models** — models running entirely on your own machine, free and private

A council of a local Llama 3 on your PC, a cloud Gemini via direct API, 
and a GPT model via OpenRouter all debating the same question is completely valid.

### Setting up Ollama models

Ollama gives you two ways to run models: **locally** on your own PC, or on **Ollama's cloud servers**. You can use one or both at the same time.

---

#### 🖥️ Option A — Local models (free, fully private)

Local models run entirely on your own machine. Nothing is sent to the internet. They're free to use but require enough RAM (see table below) and are slower than cloud models.

**Install Ollama:**
1. Go to https://ollama.com/download
2. Click **Download for Windows** — this is a standard `.exe` installer, just like any other Windows program.
3. Run the installer and follow the prompts. Once finished, Ollama runs quietly in the background (you'll see its icon in the system tray near the clock).

**Download a model:**

Open PowerShell and run one of these commands depending on which model you want. Each one downloads a model to your PC — this may take a few minutes depending on your internet speed.
```
ollama pull llama3
ollama pull mistral
ollama pull gemma3
```
> Not sure which to pick? Start with `llama3` — it's a solid all-rounder and works well on most PCs with 8GB of RAM.

**Add it to your council** in `backend/config.py`:
```python
{
    "provider": ollama_local,
    "model": "llama3",
    "name": "Llama 3 (Local)"
}
```

**RAM requirements:**

| Model size | Minimum RAM | Example models |
|---|---|---|
| 7B | 8 GB | llama3, mistral, gemma3 |
| 13B | 16 GB | llama2:13b, codellama:13b |
| 34B | 32 GB | llama2:34b |
| 70B+ | 64 GB+ | Not recommended for most PCs |

> Not sure how much RAM your PC has? Press `Windows + Pause/Break` or search "About your PC" in the Start menu — it's listed there as "Installed RAM".

---

#### ☁️ Option B — Ollama cloud models (no local hardware needed)

Ollama also hosts models on their own servers, which you access over the internet. This means you can use large, powerful models without needing a high-end PC. Ollama has generous free daily and weekly token limits, so for most casual use you're unlikely to hit them — and no billing is required to get started.

**Get an API key:**
1. Go to https://ollama.com and create an account.
2. Navigate to your account settings and generate an API key.
3. Add it to your `.env` file:
```
OLLAMA_CLOUD_API_KEY=...
```

**Pull the model** in PowerShell using the `:cloud` tag:
```
ollama pull llama3:70b:cloud
```

**Then add it to your council** in `backend/config.py`:
```python
{
    "provider": ollama_cloud,
    "model": "llama3:70b",
    "name": "Llama 3 70B (Cloud)"
}
```

> The difference from local is just `ollama_cloud` instead of `ollama_local` as the provider — everything else works the same way.

---

> 💡 **You can mix both.** A council with a local 7B model on your PC *and* a large cloud model on Ollama's servers is completely valid — and costs less than running everything through OpenAI.

### Step 4 — Configure your models

Edit `backend/config.py` to set up your council.
> To open this file: in File Explorer, go to `Documents → model-behavior → backend` and open `config.py` with Notepad (right-click → Open with → Notepad). Each model needs a `provider`, `model`, and `name`:

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

---
## Changelog
Consult changes [here](CHANGELOG.md)

---
## Tech Stack

- **Backend:** FastAPI (Python), async, multi-provider LLM support
- **Frontend:** React + Vite, streaming SSE, ReactMarkdown
- **Storage:** JSON files in `data/conversations/`
- **Package management:** uv (Python), npm (JavaScript)

---

## Credits

Based on [karpathy/llm-council](https://github.com/karpathy/llm-council) by Andrej Karpathy, who built the original 3-stage council concept and explicitly invited the community to take it further. This is Niiblr's attempt at doing exactly that.

*Niiblr is a personal handle. Unlikely affiliation with the Futurama character.*
