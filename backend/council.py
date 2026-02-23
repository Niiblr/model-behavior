"""3-stage LLM Council orchestration with multi-provider support."""

from typing import List, Dict, Any, Tuple
from .providers import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_CONFIG


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
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage1_results = []
    for model_name, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model_name,
                "response": response.get('content', '')
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

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model_name, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
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

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

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
        messages
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

    # Use chairman for title generation
    chairman_provider = CHAIRMAN_CONFIG["provider"]
    chairman_model = CHAIRMAN_CONFIG["model"]
    
    response = await query_model(
        chairman_provider,
        chairman_model,
        messages,
        timeout=30.0
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
    Same as Stage 1 in council mode — establishes shared understanding.
    """
    return await stage1_collect_responses(user_query)


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
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    return [
        {"model": name, "response": r.get('content', '')}
        for name, r in responses.items()
        if r is not None
    ]


async def hybrid_phase3_devils_advocate(
    user_query: str,
    phase1_results: List[Dict[str, Any]],
    phase2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Hybrid Phase 3 (Devil's Advocate): The Chairman identifies the emerging
    consensus and argues against it as forcefully as possible.
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

    response = await query_model(
        CHAIRMAN_CONFIG["provider"],
        CHAIRMAN_CONFIG["model"],
        messages
    )

    return {
        "model": f"Devil's Advocate ({CHAIRMAN_CONFIG['name']})",
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
    p1_text = _build_responses_text(phase1_results)
    p2_text = _build_responses_text(phase2_results)

    synthesis_prompt = f"""You are the Chairman of an AI Council. The council has completed a full hybrid debate process on a question. Your job is to deliver the final, definitive answer.

Original Question: {user_query}

PHASE 1 — Socratic (Initial Understanding):
{p1_text}

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