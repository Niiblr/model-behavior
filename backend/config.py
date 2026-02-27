"""Configuration for the LLM Council with multi-provider support."""

import os
from dotenv import load_dotenv
from .providers.openrouter import OpenRouterProvider
from .providers.ollama import OllamaProvider
from .providers.gemini import GeminiProvider
from .providers.openai import OpenAIProvider

load_dotenv()

# ============================================================================
# API KEYS - Add your keys to the .env file
# ============================================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================================================
# PROVIDERS
# Note: For Ollama, local vs cloud is determined by the model name itself.
#       Models ending in ':cloud' are routed to Ollama Cloud automatically.
#       Models without ':cloud' run on your local machine.
# ============================================================================

# --- Direct API Providers ---
openrouter = OpenRouterProvider(OPENROUTER_API_KEY) if OPENROUTER_API_KEY else None
gemini = GeminiProvider(GOOGLE_API_KEY) if GOOGLE_API_KEY else None
openai = OpenAIProvider(OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- Ollama (handles both local and cloud models) ---
ollama = OllamaProvider(base_url="http://localhost:11434")

# ============================================================================
# COUNCIL CONFIGURATION
# ============================================================================

COUNCIL_MODELS = [
    # --- Direct API ---
    {
        "provider": gemini,
        "model": "gemini-flash-latest",
        "name": "Gemini 3 Flash"
    },

    # --- Ollama Cloud (model name ends in ':cloud') ---
    {
        "provider": ollama,
        "model": "kimi-k2-thinking:cloud",
        "name": "Kimi K2 Thinking"
    },
    {
        "provider": ollama,
        "model": "glm-5:cloud",
        "name": "GLM-5"
    },
    {
        "provider": ollama,
        "model": "gpt-oss:120b-cloud",
        "name": "GPT-OSS 120B"
    },
#    {
#        "provider": ollama,
#        "model": "minimax-m2.5:cloud",
#        "name": "Minimax M2.5"
#    },
    {
        "provider": ollama,
        "model": "qwen3-next:80b-cloud",
        "name": "Qwen3 80B"
    },

    # --- OpenRouter (free tier) ---
    {
        "provider": openrouter,
        "model": "arcee-ai/trinity-large-preview:free",
        "name": "Arcee AI"
    },
    {
        "provider": openrouter,
        "model": "upstage/solar-pro-3:free",
        "name": "Solar Pro 3"
    },
    {
        "provider": openrouter,
        "model": "nousresearch/hermes-3-llama-3.1-405b:free",
        "name": "Hermes 3 405B"
    },
]

# Filter out any models whose provider wasn't initialized (missing API key)
COUNCIL_MODELS = [m for m in COUNCIL_MODELS if m["provider"] is not None]

# Chairman model — synthesizes the final answer
CHAIRMAN_CONFIG = {
    "provider": ollama,
    "model": "deepseek-v3.1:671b-cloud",
    "name": "Chairman DeepSeek V3.1 671B"
}

# Devil's Advocate model — challenges the emerging consensus in hybrid mode
DEVILS_ADVOCATE_CONFIG = {
    "provider": ollama,
    "model": "kimi-k2-thinking:cloud",
    "name": "Devil's Advocate Kimi K2 Thinking"
}

# Hybrid mode council — same as COUNCIL_MODELS but without the Devil's Advocate
# so it arrives fresh in Phase 3 with no prior positions
HYBRID_COUNCIL_MODELS = [
    m for m in COUNCIL_MODELS
    if m["model"] != DEVILS_ADVOCATE_CONFIG["model"]
]

# Data directory for conversation storage
DATA_DIR = "data/conversations"