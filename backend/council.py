"""3-stage LLM Council orchestration with multi-provider support."""

import asyncio
import re
from typing import List, Dict, Any, Tuple

from .providers import query_models_parallel, query_model
from .providers.openrouter import OpenRouterProvider
from .config import (
    COUNCIL_MODELS,
    HYBRID_COUNCIL_MODELS,
    CHAIRMAN_CONFIG,
    DEVILS_ADVOCATE_CONFIG,
    openrouter,
)
from .freemodels import get_free_models


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' (display name) and 'response' keys
    """
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel using the new provider system
    responses = await query_models_parallel(COUNCIL_MODELS, messages, max_tokens=4096)

    # Format results
    stage1_results = []
    for model_name, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model_name,
                "response": response.get('content', '').strip()
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

[your analysis here]
FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages, max_tokens=1500)

    # Format results
    stage2_results = []
    for model_name, response in responses.items():
        if response is not None:
            full_text = response.get('content', '').strip()
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model_name,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n".join([
        f"{result['model']}: {', '.join(result['parsed_ranking'])}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Synthesize the following models' responses and peer rankings into a definitive, final answer:

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    chairman_provider = CHAIRMAN_CONFIG["provider"]
    chairman_model = CHAIRMAN_CONFIG["model"]
    chairman_name = CHAIRMAN_CONFIG["name"]
    
    response = await query_model(
        chairman_provider,
        chairman_model,
        messages,
        max_tokens=4096
    )

    if response is None:
        # Fallback if chairman fails
        return {
            "model": chairman_name,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": chairman_name,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    from .config import gemini, openrouter
    if gemini:
        title_provider = gemini
        title_model = "gemini-flash-latest"
    elif openrouter:
        title_provider = openrouter
        title_model = "google/gemini-flash-1.5-8b"
    else:
        title_provider = CHAIRMAN_CONFIG["provider"]
        title_model = CHAIRMAN_CONFIG["model"]
    
    response = await query_model(
        title_provider,
        title_model,
        messages,
        timeout=30.0,
        max_tokens=100
    )

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata


# ============================================================================
# HYBRID COUNCIL MODE
# ============================================================================

def _build_responses_text(results: List[Dict[str, Any]]) -> str:
    """Helper: format a list of model responses into readable text."""
    return "\n\n".join([
        f"--- {result['model']} ---\n{result['response']}"
        for result in results
    ])


async def hybrid_phase1_socratic(user_query: str) -> List[Dict[str, Any]]:
    """
    Hybrid Phase 1 (Socratic): All models give their initial answer.
    Kimi K2 is excluded here so it arrives fresh as Devil's Advocate in Phase 3.
    """
    messages = [{"role": "user", "content": user_query}]
    responses = await query_models_parallel(HYBRID_COUNCIL_MODELS, messages, max_tokens=4096)
    return [
        {"model": name, "response": r.get('content', '').strip()}
        for name, r in responses.items()
        if r is not None
    ]


async def hybrid_phase2_debate(
    user_query: str,
    phase1_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Hybrid Phase 2 (Debate): Each model reads all Phase 1 responses,
    then agrees, disagrees, or adds nuance. Forces critical engagement.
    """
    responses_text = _build_responses_text(phase1_results)

    debate_prompt = f"""A question was posed to a group of AI models:

Question: {user_query}

Here are the initial responses from the group:

{responses_text}

Now it is YOUR turn to engage in the debate. Read all the responses above carefully and provide your debate response:

1. Identify 1-2 points you STRONGLY AGREE with from other responses (explain why they are correct)
2. Identify 1-2 points you DISAGREE with or find incomplete (explain what is wrong or missing)
3. Add any important nuance, counterexample, or perspective that was missed by others

Be direct and intellectually honest. Do not simply summarize the others — engage with them critically. It is perfectly fine to strongly disagree. Reference specific models or points when you respond to them."""

    messages = [{"role": "user", "content": debate_prompt}]
    responses = await query_models_parallel(HYBRID_COUNCIL_MODELS, messages, max_tokens=4096)

    return [
        {"model": name, "response": r.get('content', '').strip()}
        for name, r in responses.items()
        if r is not None
    ]


async def hybrid_phase3_devils_advocate(
    user_query: str,
    phase1_results: List[Dict[str, Any]],
    phase2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Hybrid Phase 3 (Devil's Advocate): A dedicated model separate from the
    Chairman identifies the emerging consensus and argues against it forcefully.
    """
    p1_text = _build_responses_text(phase1_results)
    p2_text = _build_responses_text(phase2_results)

    da_prompt = f"""You are playing the role of Devil's Advocate in a structured debate.

Original Question: {user_query}

PHASE 1 — Initial Responses:
{p1_text}

PHASE 2 — Debate Responses:
{p2_text}

Your task:
1. First, identify the EMERGING CONSENSUS — what view or answer is the group converging on?
2. Then, argue AGAINST that consensus as forcefully and intelligently as possible.

Find the weakest assumptions. Identify what risks or downsides were ignored.
Point out counterexamples. Challenge things that were taken for granted.
Play devil's advocate fully — your job is to stress-test the group's thinking,
not to be agreeable. Even if you personally agree with the consensus, argue against it."""

    messages = [{"role": "user", "content": da_prompt}]

    # Use the dedicated Devil's Advocate model (separate from Chairman)
    # No max_tokens cap — thinking models (e.g. Kimi K2) need uncapped budget
    response = await query_model(
        DEVILS_ADVOCATE_CONFIG["provider"],
        DEVILS_ADVOCATE_CONFIG["model"],
        messages
    )

    return {
        "model": f"Devil's Advocate ({DEVILS_ADVOCATE_CONFIG['name']})",
        "response": response.get('content', '') if response else "Error: Devil's Advocate failed to respond."
    }


async def hybrid_phase4_synthesis(
    user_query: str,
    phase1_results: List[Dict[str, Any]],
    phase2_results: List[Dict[str, Any]],
    phase3_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Hybrid Phase 4 (Chairman Synthesis): Having seen all phases — initial answers,
    debate, and devil's advocate challenge — the Chairman delivers the final answer.
    """
    p2_text = _build_responses_text(phase2_results)

    synthesis_prompt = f"""You are the Chairman of an AI Council. The council has completed a full hybrid debate process on a question. Your job is to deliver the final, definitive answer.

Original Question: {user_query}

PHASE 2 — Debate (Agreements, Disagreements, Nuance):
{p2_text}

PHASE 3 — Devil's Advocate (Challenge to Consensus):
Devil's Advocate ({phase3_result['model']}): {phase3_result['response']}

Now synthesize everything. Your final answer should:
- Reflect the strongest arguments from all phases
- Acknowledge genuine areas of disagreement or uncertainty
- Take seriously the devil's advocate challenge (either refute it or incorporate it)
- Be the most complete, honest, and well-reasoned answer possible

This is the council's final word on the question."""

    messages = [{"role": "user", "content": synthesis_prompt}]

    # No max_tokens cap — this is the final user-facing answer
    response = await query_model(
        CHAIRMAN_CONFIG["provider"],
        CHAIRMAN_CONFIG["model"],
        messages
    )

    return {
        "model": f"Chairman ({CHAIRMAN_CONFIG['name']})",
        "response": response.get('content', '') if response else "Error: Chairman synthesis failed."
    }


async def run_hybrid_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 4-phase hybrid council process:
    Phase 1: Socratic (initial answers)
    Phase 2: Debate (challenge each other)
    Phase 3: Devil's Advocate (challenge the consensus)
    Phase 4: Chairman Synthesis (final answer)
    """
    # Phase 1: Socratic — initial answers
    phase1_results = await hybrid_phase1_socratic(user_query)

    if not phase1_results:
        return [], [], {"model": "error", "response": "All models failed in Phase 1."}, {}

    # Phase 2: Debate — challenge and respond
    phase2_results = await hybrid_phase2_debate(user_query, phase1_results)

    # Phase 3: Devil's Advocate — challenge the consensus
    phase3_result = await hybrid_phase3_devils_advocate(user_query, phase1_results, phase2_results)

    # Phase 4: Chairman Synthesis — final answer
    phase4_result = await hybrid_phase4_synthesis(user_query, phase1_results, phase2_results, phase3_result)

    metadata = {"mode": "hybrid"}

    return phase1_results, phase2_results, phase3_result, phase4_result, metadata


# ============================================================================
# CONSENSUS DEBATE MODE
# ============================================================================
# A dynamic council assembled from free OpenRouter models (discovered via the
# models.dev catalog). Models debate in rounds, voting after each round on
# whether the group has converged. Strict majority ends the debate; the
# Chairman — one of the participants, who abstains from voting — verifies that
# majority positions actually align before declaring consensus.
# ============================================================================

CONSENSUS_MAX_FAILURES = 2      # consecutive failures before a model is dropped
CONSENSUS_MIN_QUORUM = 3        # minimum active models to keep debating
CONSENSUS_STAGGER_SECONDS = 5   # spacing between OpenRouter launches (free-tier rate limits)
CONSENSUS_QUERY_TIMEOUT = 300.0 # per-model timeout (thinking free models can be slow)

_VERDICT_RE = re.compile(r"CONSENSUS\s*[:\-]\s*(YES|NO)", re.IGNORECASE)
_POSITION_RE = re.compile(r"FINAL POSITION\s*[:\-]\s*([\s\S]+)$", re.IGNORECASE)
_ALIGNED_RE = re.compile(r"VERDICT\s*[:\-]\s*(ALIGNED|CONFLICTED)", re.IGNORECASE)


def parse_verdict_text(text: str) -> Tuple[str, str, str]:
    """
    Parse the structured verdict block from a debate statement.

    Returns:
        Tuple of (verdict "YES"/"NO"/None, final_position text/None,
        display_text with the structured block stripped out).
    """
    verdict = None
    position = None

    match = _VERDICT_RE.search(text)
    if match:
        verdict = match.group(1).upper()

    pos_match = _POSITION_RE.search(text)
    if pos_match:
        position = pos_match.group(1).strip()

    # Strip the structured tail from the text shown to the user
    display = _VERDICT_RE.sub("", text)
    display = _POSITION_RE.sub("", display)
    display = re.sub(r"\n{3,}$", "\n\n", display).strip()

    return verdict, position, display


async def _resolve_participant_configs(
    model_ids: List[str],
    chairman_id: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Resolve selected model ids into provider configs using the free catalog."""
    if openrouter is None:
        raise RuntimeError("OPENROUTER_API_KEY is not configured; consensus debates require it (free tier is fine).")

    catalog = await get_free_models()
    by_id = {m["id"]: m for m in catalog}

    def build(model_id: str) -> Dict[str, Any]:
        info = by_id.get(model_id)
        if info is None:
            raise ValueError(f"Model '{model_id}' is not in the current free-model catalog.")
        return {
            "provider": openrouter,
            "model": info["id"],
            "name": info["name"],
            "id": info["id"],
        }

    seen = set()
    participants = []
    for mid in model_ids:
        if mid == chairman_id or mid in seen:
            continue
        seen.add(mid)
        participants.append(build(mid))

    chairman = build(chairman_id)
    return participants, chairman


def _format_transcript(rounds: List[Dict[str, Any]], own_name: str) -> str:
    """Format prior rounds into a readable transcript, marking the caller's entries."""
    parts = []
    for round_entry in rounds:
        lines = [f"=== ROUND {round_entry['round']} ==="]
        for stmt in round_entry["statements"]:
            marker = " (you)" if stmt["model"] == own_name else ""
            status = ""
            if stmt.get("failed"):
                status = " [failed to respond this round]"
            elif stmt.get("verdict"):
                status = f" [voted CONSENSUS: {stmt['verdict']}]"
            lines.append(f"--- {stmt['model']}{marker}{status} ---")
            lines.append(stmt["response"])
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _build_initial_prompt(user_query: str) -> str:
    return f"""A diverse council of AI models is convening to reach a shared consensus answer.

Question: {user_query}

Provide your initial position on this question. Be substantive, precise and clear — your fellow council members will read it, critique it, and build on it in later rounds."""


def _build_debate_prompt(
    user_query: str,
    round_num: int,
    max_rounds: int,
    transcript: str,
    chairman_note: str = ""
) -> str:
    note_block = f"\nCHAIRMAN'S NOTE: {chairman_note}\n" if chairman_note else ""
    return f"""You are a member of an AI council debating a question. This is debate round {round_num} of at most {max_rounds}.{note_block}

Original Question: {user_query}

TRANSCRIPT SO FAR:
{transcript}

Write your contribution to this round:
1. Respond directly to what other members said — agree where they are right, push back where they are wrong, correct factual errors.
2. Move the group toward one precise shared answer.
3. End your message EXACTLY with this format:

CONSENSUS: YES or NO
FINAL POSITION: <one paragraph summarizing your current best answer>

Vote YES only if you believe the council has effectively converged on a shared answer (differences of wording or emphasis are fine). Vote NO if material disagreement remains."""


def _build_review_prompt(
    user_query: str,
    yes_positions: List[Dict[str, str]]
) -> str:
    positions_text = "\n\n".join([
        f"--- {p['model']} ---\n{p['position']}"
        for p in yes_positions
    ])
    return f"""You are the Chairman of an AI council. The members just voted, and a strict majority declared that consensus has been reached on this question:

{user_query}

The majority's final positions:

{positions_text}

Before consensus can be declared, verify these positions genuinely align. They may differ in wording, emphasis or level of detail — that is acceptable. They conflict only if they assert materially different answers or recommendations.

Reply in EXACTLY this format:

VERDICT: ALIGNED or CONFLICTED
REASONING: <one or two sentences explaining your judgment>"""


def _parse_review(text: str) -> Dict[str, Any]:
    aligned = None
    reasoning = (text or "").strip()
    match = _ALIGNED_RE.search(text or "")
    if match:
        aligned = match.group(1).upper() == "ALIGNED"
    reason_match = re.search(r"REASONING\s*[:\-]\s*([\s\S]+)$", text or "", re.IGNORECASE)
    if reason_match:
        reasoning = reason_match.group(1).strip()
    return {"aligned": aligned, "reasoning": reasoning}


def _build_synthesis_prompt(
    user_query: str,
    transcript: str,
    final_positions: List[Dict[str, str]],
    dissent: List[Dict[str, str]],
    consensus_declared: bool
) -> str:
    positions_text = "\n\n".join([
        f"--- {p['model']} ---\n{p['position'] or p['response']}"
        for p in final_positions
    ])
    dissent_text = ""
    if dissent:
        dissent_text = "DISSENTING VIEWS (not part of the consensus):\n" + "\n\n".join([
            f"--- {d['model']} ---\n{d['position'] or d['response']}"
            for d in dissent
        ])

    framing = (
        "A strict majority of the council voted that consensus was reached."
        if consensus_declared
        else "The council hit the round limit without a formal majority — you must judge what shared ground exists."
    )

    return f"""You are the Chairman of an AI council that has just concluded a multi-round debate. Your task is to deliver the council's final answer.

Original Question: {user_query}

{framing}

FULL DEBATE TRANSCRIPT:
{transcript}

MEMBERS' FINAL POSITIONS:
{positions_text}

{dissent_text}

Write the definitive answer to the user's question:
- Reflect the converged view of the council
- Incorporate the strongest refinements made during the debate
- If there is dissent or unresolved uncertainty, acknowledge it honestly in a brief closing note
- Be clear, complete and well-reasoned — this is the council's final word"""


async def run_consensus_debate_stream(
    user_query: str,
    model_ids: List[str],
    chairman_id: str,
    max_rounds: int = 4
):
    """
    Async generator orchestrating a consensus debate. Yields SSE-ready event
    dicts as they happen so the frontend can witness the debate live.

    Events yielded:
        consensus_start          {participants, chairman, max_rounds}
        consensus_round_start    {round}
        consensus_model_complete {round, statement}
        consensus_round_complete {round, votes, reached}
        consensus_chairman_review {aligned, reasoning}
        consensus_chairman_start {}
        consensus_synthesis_complete {model, response}
    """
    participants, chairman = await _resolve_participant_configs(list(model_ids), chairman_id)

    all_members = [
        {"id": m["id"], "name": m["name"]} for m in participants + [chairman]
    ]
    yield {
        "type": "consensus_start",
        "data": {
            "participants": [{"id": m["id"], "name": m["name"]} for m in participants],
            "chairman": {"id": chairman["id"], "name": chairman["name"]},
            "max_rounds": max_rounds,
        },
    }

    failures: Dict[str, int] = {m["name"]: 0 for m in participants}
    rounds: List[Dict[str, Any]] = []
    chairman_note = ""
    consensus_declared = False

    async def query_one(config: Dict[str, Any], messages: List[Dict[str, str]], delay: float):
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            response = await query_model(
                config["provider"],
                config["model"],
                messages,
                timeout=CONSENSUS_QUERY_TIMEOUT,
            )
        except Exception as e:
            print(f"[consensus] Error querying {config['name']}: {e}")
            response = None
        return config["name"], response

    async def run_round_parallel(active: List[Dict[str, Any]], messages_builder) -> List[Tuple[str, Any]]:
        """Fire all queries staggered; return results in completion order."""
        tasks = [
            asyncio.ensure_future(query_one(cfg, messages_builder(cfg), i * CONSENSUS_STAGGER_SECONDS))
            for i, cfg in enumerate(active)
        ]
        results = []
        for future in asyncio.as_completed(tasks):
            results.append(await future)
        return results

    def active_configs() -> List[Dict[str, Any]]:
        return [m for m in participants if failures[m["name"]] < CONSENSUS_MAX_FAILURES]

    async def query_chairman(messages: List[Dict[str, str]]):
        """
        Query the designated chairman; if it fails (e.g. its free endpoint is
        rate-limited), fall back to other healthy participants so the debate
        always produces a synthesis.
        Returns (response, config_used).
        """
        candidates = [chairman] + [
            m for m in active_configs() if m["model"] != chairman["model"]
        ]
        for cand in candidates:
            response = None
            try:
                response = await query_model(
                    cand["provider"],
                    cand["model"],
                    messages,
                    timeout=CONSENSUS_QUERY_TIMEOUT,
                )
            except Exception as e:
                print(f"[consensus] Chairman candidate {cand['name']} errored: {e}")
                response = None
            if response and (response.get("content") or "").strip():
                return response, cand
            print(f"[consensus] Chairman candidate {cand['name']} unavailable; trying next.")
        return None, None

    # ------------------------------------------------------------------
    # ROUND 0 — initial positions (no vote yet)
    # ------------------------------------------------------------------
    yield {"type": "consensus_round_start", "data": {"round": 0}}

    round_zero_statements = []
    for name, response in await run_round_parallel(
        active_configs(),
        lambda cfg: [{"role": "user", "content": _build_initial_prompt(user_query)}],
    ):
        if response is None:
            failures[name] = failures.get(name, 0) + 1
            statement = {"model": name, "response": "", "verdict": None, "position": None, "failed": True}
        else:
            statement = {
                "model": name,
                "response": (response.get("content") or "").strip(),
                "verdict": None,
                "position": None,
                "failed": False,
            }
        round_zero_statements.append(statement)
        yield {
            "type": "consensus_model_complete",
            "data": {"round": 0, "statement": statement},
        }

    rounds.append({
        "round": 0,
        "statements": round_zero_statements,
        "votes": {"yes": [], "no": []},
        "reached": False,
    })
    yield {
        "type": "consensus_round_complete",
        "data": {"round": 0, "votes": {"yes": [], "no": []}, "reached": False},
    }

    # ------------------------------------------------------------------
    # DEBATE ROUNDS 1..N
    # ------------------------------------------------------------------
    for round_num in range(1, max_rounds + 1):
        active = active_configs()
        if len(active) < CONSENSUS_MIN_QUORUM:
            print(f"[consensus] Quorum lost ({len(active)} active); moving to synthesis.")
            break

        yield {"type": "consensus_round_start", "data": {"round": round_num}}

        def builder(cfg, _rn=round_num):
            transcript = _format_transcript(rounds, cfg["name"])
            return [{"role": "user", "content": _build_debate_prompt(
                user_query, _rn, max_rounds, transcript, chairman_note
            )}]

        statements = []
        yes_voters, no_voters = [], []

        for name, response in await run_round_parallel(active, builder):
            if response is None:
                failures[name] = failures.get(name, 0) + 1
                statement = {"model": name, "response": "", "verdict": None, "position": None, "failed": True}
            else:
                raw = (response.get("content") or "").strip()
                verdict, position, display = parse_verdict_text(raw)
                statement = {
                    "model": name,
                    "response": display,
                    "verdict": verdict,
                    "position": position,
                    "failed": False,
                }
                if verdict == "YES":
                    yes_voters.append(name)
                else:
                    # Missing/malformed verdict counts as NO — cautious by default
                    no_voters.append(name)
                    if verdict is None:
                        statement["verdict"] = "NO"
                        statement["malformed"] = True

            statements.append(statement)
            yield {
                "type": "consensus_model_complete",
                "data": {"round": round_num, "statement": statement},
            }

        voters = len(yes_voters) + len(no_voters)
        reached = voters > 0 and (len(yes_voters) * 2 > voters)

        review_data = None
        if reached:
            # Chairman (a participant, abstained from voting) verifies alignment
            yes_positions = [
                {"model": s["model"], "position": s["position"] or s["response"]}
                for s in statements if s["verdict"] == "YES"
            ]
            review_response, reviewer_cfg = await query_chairman(
                [{"role": "user", "content": _build_review_prompt(user_query, yes_positions)}]
            )
            review_data = _parse_review((review_response or {}).get("content") or "")
            if not (review_response or {}).get("content"):
                # No chairman candidate could be queried — accept the majority
                review_data = {
                    "aligned": True,
                    "reasoning": "Chairman review unavailable; accepting majority vote.",
                }
                reviewer_cfg = chairman

            review_data["reviewer"] = (
                f"{reviewer_cfg['name']} (acting)" if reviewer_cfg["model"] != chairman["model"]
                else reviewer_cfg["name"]
            )
            yield {"type": "consensus_chairman_review", "data": review_data}

            if review_data["aligned"]:
                reached = True
                rounds.append({
                    "round": round_num,
                    "statements": statements,
                    "votes": {"yes": yes_voters, "no": no_voters},
                    "reached": True,
                    "review": review_data,
                })
                yield {
                    "type": "consensus_round_complete",
                    "data": {"round": round_num, "votes": {"yes": yes_voters, "no": no_voters}, "reached": True},
                }
                consensus_declared = True
                break
            else:
                # Positions conflicted — force another reconciliation round
                chairman_note = (
                    f"In the previous round a majority voted YES, but your review found their "
                    f"final positions materially conflicting ({review_data['reasoning']}). "
                    f"This round exists solely to reconcile those differences."
                )
                reached = False

        rounds.append({
            "round": round_num,
            "statements": statements,
            "votes": {"yes": yes_voters, "no": no_voters},
            "reached": reached,
            **({"review": review_data} if review_data else {}),
        })
        yield {
            "type": "consensus_round_complete",
            "data": {"round": round_num, "votes": {"yes": yes_voters, "no": no_voters}, "reached": reached},
        }

    # ------------------------------------------------------------------
    # CHAIRMAN SYNTHESIS
    # ------------------------------------------------------------------
    yield {"type": "consensus_chairman_start", "data": {}}

    last_statements = rounds[-1]["statements"] if rounds else []
    final_positions = [s for s in last_statements if not s.get("failed")]
    dissent = [s for s in final_positions if s.get("verdict") == "NO"]

    synthesis_response, synthesis_cfg = await query_chairman(
        [{"role": "user", "content": _build_synthesis_prompt(
            user_query,
            _format_transcript(rounds, chairman["name"]),
            final_positions,
            dissent,
            consensus_declared,
        )}]
    )

    if not (synthesis_response or {}).get("content"):
        synthesis = {
            "model": f"Chairman ({chairman['name']})",
            "response": "Error: All chairman candidates failed to respond — no synthesis could be produced.",
        }
    else:
        label = (
            f"Chairman ({synthesis_cfg['name']}, acting)"
            if synthesis_cfg["model"] != chairman["model"]
            else f"Chairman ({synthesis_cfg['name']})"
        )
        synthesis = {
            "model": label,
            "response": (synthesis_response.get("content") or "").strip(),
        }
    yield {"type": "consensus_synthesis_complete", "data": synthesis}


async def get_free_models_endpoint() -> List[Dict[str, Any]]:
    """Convenience wrapper for the API endpoint."""
    return await get_free_models()