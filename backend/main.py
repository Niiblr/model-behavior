"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
    run_hybrid_council,
    hybrid_phase1_socratic,
    hybrid_phase2_debate,
    hybrid_phase3_devils_advocate,
    hybrid_phase4_synthesis,
)

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    mode: str = "council"  # "council" = original 3-stage, "hybrid" = new 4-phase hybrid


class RenameConversationRequest(BaseModel):
    """Request to rename a conversation."""
    title: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0

    storage.add_user_message(conversation_id, request.content)

    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            storage.add_user_message(conversation_id, request.content)

            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/conversations/{conversation_id}/message/stream/hybrid")
async def send_message_stream_hybrid(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 4-phase hybrid council process.
    Phase 1: Socratic | Phase 2: Debate | Phase 3: Devil's Advocate | Phase 4: Synthesis
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            storage.add_user_message(conversation_id, request.content)

            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            yield f"data: {json.dumps({'type': 'hybrid_phase1_start'})}\n\n"
            phase1_results = await hybrid_phase1_socratic(request.content)
            yield f"data: {json.dumps({'type': 'hybrid_phase1_complete', 'data': phase1_results})}\n\n"

            yield f"data: {json.dumps({'type': 'hybrid_phase2_start'})}\n\n"
            phase2_results = await hybrid_phase2_debate(request.content, phase1_results)
            yield f"data: {json.dumps({'type': 'hybrid_phase2_complete', 'data': phase2_results})}\n\n"

            yield f"data: {json.dumps({'type': 'hybrid_phase3_start'})}\n\n"
            phase3_result = await hybrid_phase3_devils_advocate(request.content, phase1_results, phase2_results)
            yield f"data: {json.dumps({'type': 'hybrid_phase3_complete', 'data': phase3_result})}\n\n"

            yield f"data: {json.dumps({'type': 'hybrid_phase4_start'})}\n\n"
            phase4_result = await hybrid_phase4_synthesis(request.content, phase1_results, phase2_results, phase3_result)
            yield f"data: {json.dumps({'type': 'hybrid_phase4_complete', 'data': phase4_result})}\n\n"

            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            hybrid_message = {
                "role": "assistant",
                "mode": "hybrid",
                "hybrid_phase1": phase1_results,
                "hybrid_phase2": phase2_results,
                "hybrid_phase3": phase3_result,
                "hybrid_phase4": phase4_result,
                "stage1": [],
                "stage2": [],
                "stage3": None,
                "metadata": {"mode": "hybrid"}
            }
            conversation = storage.get_conversation(conversation_id)
            conversation["messages"].append(hybrid_message)
            storage.save_conversation(conversation)

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.delete("/api/conversations/{conversation_id}/messages")
async def clear_messages(conversation_id: str):
    """Clear all messages from a conversation but keep the conversation."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation["messages"] = []
    storage.save_conversation(conversation)

    return {"success": True, "message": "Messages cleared"}


@app.put("/api/conversations/{conversation_id}/title")
async def rename_conversation(conversation_id: str, request: RenameConversationRequest):
    """Rename a conversation."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    storage.update_conversation_title(conversation_id, request.title)

    return {"success": True, "title": request.title}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation entirely."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    storage.delete_conversation(conversation_id)

    return {"success": True, "message": "Conversation deleted"}


@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str):
    """Export a conversation as markdown."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    markdown = f"# {conversation['title']}\n\n"
    markdown += f"*Created: {conversation['created_at']}*\n\n"
    markdown += "---\n\n"

    for message in conversation["messages"]:
        if message["role"] == "user":
            markdown += f"## User\n\n{message['content']}\n\n"
        elif message["role"] == "assistant":
            if message.get("mode") == "hybrid":
                markdown += "## Hybrid Council Response\n\n"

                markdown += "### Phase 1: Socratic (Initial Responses)\n\n"
                for response in message.get("hybrid_phase1", []):
                    markdown += f"**{response['model']}:**\n\n{response['response']}\n\n"

                markdown += "### Phase 2: Debate\n\n"
                for response in message.get("hybrid_phase2", []):
                    markdown += f"**{response['model']}:**\n\n{response['response']}\n\n"

                markdown += "### Phase 3: Devil's Advocate\n\n"
                p3 = message.get("hybrid_phase3") or {}
                if p3.get("response"):
                    markdown += f"**{p3['model']}:**\n\n{p3['response']}\n\n"

                markdown += "### Phase 4: Final Synthesis\n\n"
                p4 = message.get("hybrid_phase4") or {}
                if p4.get("response"):
                    markdown += f"**{p4['model']}:**\n\n{p4['response']}\n\n"

            else:
                markdown += "## LLM Council Response\n\n"

                markdown += "### Stage 1: Individual Responses\n\n"
                for response in message.get("stage1", []):
                    markdown += f"**{response['model']}:**\n\n{response['response']}\n\n"

                markdown += "### Stage 2: Peer Rankings\n\n"
                for ranking in message.get("stage2", []):
                    markdown += f"**{ranking['model']}:**\n\n{ranking['ranking']}\n\n"

                markdown += "### Stage 3: Final Synthesis\n\n"
                stage3 = message.get("stage3") or {}
                if stage3.get("response"):
                    markdown += f"**{stage3['model']}:**\n\n{stage3['response']}\n\n"

            markdown += "---\n\n"

    return {
        "markdown": markdown,
        "filename": f"{conversation['title'].replace(' ', '_')}.md"
    }


@app.get("/api/conversations/{conversation_id}/export/html")
async def export_conversation_html(conversation_id: str):
    """Export a conversation as a self-contained HTML page."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    sections = []
    for message in conversation["messages"]:
        if message["role"] == "user":
            sections.append({
                "type": "user",
                "content": message["content"]
            })
        elif message["role"] == "assistant":
            if message.get("mode") == "hybrid":
                sections.append({
                    "type": "hybrid",
                    "hybrid_phase1": message.get("hybrid_phase1", []),
                    "hybrid_phase2": message.get("hybrid_phase2", []),
                    "hybrid_phase3": message.get("hybrid_phase3") or {},
                    "hybrid_phase4": message.get("hybrid_phase4") or {},
                })
            else:
                stage1_items = [
                    {"model": r["model"], "response": r["response"]}
                    for r in message.get("stage1", [])
                ]
                stage2_items = [
                    {"model": r["model"], "ranking": r["ranking"]}
                    for r in message.get("stage2", [])
                ]
                stage3 = message.get("stage3") or {}
                sections.append({
                    "type": "assistant",
                    "stage1": stage1_items,
                    "stage2": stage2_items,
                    "stage3": stage3
                })

    import json as _json
    sections_json = _json.dumps(sections)
    title_escaped = conversation["title"].replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&#39;')
    created_at = conversation["created_at"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title_escaped} — LLM Council</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f8fafc;
      color: #1e293b;
      margin: 0;
      padding: 24px;
    }}
    .page-header {{
      max-width: 900px;
      margin: 0 auto 32px;
      padding-bottom: 16px;
      border-bottom: 2px solid #e2e8f0;
    }}
    .page-header h1 {{
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0 0 6px;
    }}
    .page-header .meta {{ color: #64748b; font-size: 13px; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    .message {{ margin-bottom: 28px; border-radius: 12px; overflow: hidden; }}
    .user-message {{
      background: linear-gradient(135deg, #dbeafe, #bfdbfe);
      border: 1px solid #93c5fd;
      padding: 20px 24px;
    }}
    .user-label {{
      font-weight: 700;
      color: #1e40af;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }}
    .user-text {{ color: #1e293b; line-height: 1.7; white-space: pre-wrap; }}
    .assistant-message {{
      background: #fff;
      border: 1px solid #e2e8f0;
      box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }}
    .hybrid-header {{
      padding: 12px 20px;
      background: linear-gradient(135deg, #1e1b4b, #312e81);
      color: white;
      font-weight: 700;
      font-size: 15px;
    }}
    .stage-block {{ padding: 20px 24px; border-bottom: 1px solid #f1f5f9; }}
    .stage-block:last-child {{ border-bottom: none; }}
    .stage-heading {{
      font-size: 16px;
      font-weight: 700;
      color: #2563eb;
      margin: 0 0 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .stage-heading::before {{
      content: '';
      display: inline-block;
      width: 4px;
      height: 18px;
      background: linear-gradient(180deg, #2563eb, #3b82f6);
      border-radius: 2px;
    }}
    .tabs {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }}
    .tab-btn {{
      padding: 7px 14px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      background: #f8fafc;
      color: #64748b;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.15s;
    }}
    .tab-btn:hover {{ background: #f1f5f9; color: #2563eb; }}
    .tab-btn.active {{
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      color: #fff;
      border-color: #2563eb;
    }}
    .tab-panel {{ display: none; }}
    .tab-panel.visible {{ display: block; }}
    .md-content {{
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px 20px;
      line-height: 1.75;
    }}
    .md-content h1,.md-content h2,.md-content h3 {{
      color: #1e293b; margin-top: 1.2em; margin-bottom: 0.5em;
    }}
    .md-content p {{ margin: 0.6em 0; }}
    .md-content code {{
      background: #f1f5f9; padding: 2px 6px;
      border-radius: 4px; font-size: 0.9em; color: #0f172a;
    }}
    .md-content pre {{
      background: #1e293b; color: #e2e8f0;
      padding: 14px 16px; border-radius: 8px; overflow-x: auto;
    }}
    .md-content pre code {{ background: none; color: inherit; padding: 0; }}
    .md-content blockquote {{
      border-left: 4px solid #3b82f6;
      margin: 0; padding: 8px 16px; color: #475569;
    }}
    .md-content ul, .md-content ol {{ padding-left: 24px; }}
    .md-content table {{ border-collapse: collapse; width: 100%; }}
    .md-content th, .md-content td {{
      border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left;
    }}
    .md-content th {{ background: #f8fafc; font-weight: 600; }}
    .model-label {{
      font-size: 11px; font-family: monospace;
      color: #94a3b8; margin-bottom: 8px;
    }}
    .stage3-block {{
      background: linear-gradient(135deg, #d1fae5, #a7f3d0);
      border-bottom: none;
    }}
    .stage3-block .md-content {{ border-color: #6ee7b7; }}
    .stage3-block .md-content h1,
    .stage3-block .md-content h2,
    .stage3-block .md-content h3 {{ color: #059669; }}
    .aggregate-box {{
      margin-top: 16px;
      background: linear-gradient(135deg, #dbeafe, #bfdbfe);
      border: 1px solid #93c5fd;
      border-radius: 10px;
      padding: 16px 20px;
    }}
    .aggregate-box h4 {{ color: #1e40af; margin: 0 0 10px; font-size: 15px; }}
    .rank-row {{
      display: flex; align-items: center; gap: 12px;
      padding: 10px 14px; margin-bottom: 8px;
      background: #fff; border-radius: 8px;
      border: 1px solid #93c5fd;
    }}
    .rank-pos {{ font-weight: 700; color: #2563eb; font-size: 18px; min-width: 36px; }}
    .rank-model {{ flex: 1; font-size: 14px; font-weight: 500; }}
    .rank-avg {{ font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="page-header">
    <h1>{title_escaped}</h1>
    <div class="meta">Model Behavior by Niiblr &mdash; {created_at}</div>
  </div>
  <div class="container" id="root"></div>

  <script>
    const sections = {sections_json};

    function md(text) {{
      return marked.parse(text || '');
    }}

    function shortModel(m) {{
      return (m || '').split('/')[1] || m;
    }}

    let tabCounters = 0;

    function buildTabs(items, labelFn, contentFn) {{
      const groupId = 'tg' + (tabCounters++);
      const tabsHtml = items.map((item, i) =>
        `<button class="tab-btn ${{i===0?'active':''}}" onclick="selectTab('${{groupId}}',${{i}},this)">${{labelFn(item, i)}}</button>`
      ).join('');
      const panelsHtml = items.map((item, i) =>
        `<div class="tab-panel ${{i===0?'visible':''}}" id="${{groupId}}-panel-${{i}}">${{contentFn(item, i)}}</div>`
      ).join('');
      return `<div class="tabs">${{tabsHtml}}</div>${{panelsHtml}}`;
    }}

    function selectTab(groupId, idx, btn) {{
      const group = btn.closest('.stage-block, .assistant-message');
      group.querySelectorAll(`[id^="${{groupId}}-panel-"]`).forEach((p,i) => {{
        p.classList.toggle('visible', i===idx);
      }});
      btn.parentElement.querySelectorAll('.tab-btn').forEach((b,i) => {{
        b.classList.toggle('active', i===idx);
      }});
    }}

    const root = document.getElementById('root');

    sections.forEach((section, si) => {{
      const div = document.createElement('div');
      div.className = 'message';

      if (section.type === 'user') {{
        div.className += ' user-message';
        div.innerHTML = `<div class="user-label">You</div><div class="user-text">${{escHtml(section.content)}}</div>`;

      }} else if (section.type === 'hybrid') {{
        div.className += ' assistant-message';

        const phases = [
          {{ label: '💬 Phase 1: Socratic', items: section.hybrid_phase1, multi: true }},
          {{ label: '⚔️ Phase 2: Debate', items: section.hybrid_phase2, multi: true }},
          {{ label: "😈 Phase 3: Devils Advocate", single: section.hybrid_phase3, multi: false }},
          {{ label: '✨ Phase 4: Final Synthesis', single: section.hybrid_phase4, multi: false }},
        ];

        let html = '<div class="hybrid-header">🔀 Hybrid Council — Socratic → Debate → Devils Advocate → Synthesis</div>';
        phases.forEach(phase => {{
          html += `<div class="stage-block"><div class="stage-heading">${{phase.label}}</div>`;
          if (phase.multi && phase.items && phase.items.length > 0) {{
            html += buildTabs(
              phase.items,
              r => escHtml(r.model),
              r => `<div class="model-label">${{escHtml(r.model)}}</div><div class="md-content">${{md(r.response)}}</div>`
            );
          }} else if (!phase.multi && phase.single && phase.single.response) {{
            html += `<div class="model-label">${{escHtml(phase.single.model||'')}}</div><div class="md-content">${{md(phase.single.response)}}</div>`;
          }}
          html += '</div>';
        }});
        div.innerHTML = html;

      }} else {{
        div.className += ' assistant-message';

        let s1Html = '';
        if (section.stage1 && section.stage1.length > 0) {{
          s1Html = buildTabs(
            section.stage1,
            (r) => shortModel(r.model),
            (r) => `<div class="model-label">${{escHtml(r.model)}}</div><div class="md-content">${{md(r.response)}}</div>`
          );
        }}

        let s2Html = '';
        if (section.stage2 && section.stage2.length > 0) {{
          s2Html = buildTabs(
            section.stage2,
            (r) => shortModel(r.model),
            (r) => `<div class="model-label">${{escHtml(r.model)}}</div><div class="md-content">${{md(r.ranking)}}</div>`
          );
        }}

        const s3 = section.stage3 || {{}};
        const s3Html = s3.response
          ? `<div class="model-label">${{escHtml(s3.model||'')}}</div><div class="md-content">${{md(s3.response)}}</div>`
          : '<em>Not available</em>';

        div.innerHTML = `
          <div class="stage-block">
            <div class="stage-heading">Stage 1: Individual Responses</div>
            ${{s1Html}}
          </div>
          <div class="stage-block">
            <div class="stage-heading">Stage 2: Peer Rankings</div>
            ${{s2Html}}
          </div>
          <div class="stage-block stage3-block">
            <div class="stage-heading">Stage 3: Final Synthesis</div>
            ${{s3Html}}
          </div>
        `;
      }}

      root.appendChild(div);
    }});

    function escHtml(str) {{
      return String(str)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;');
    }}
  </script>
</body>
</html>"""

    safe_title = conversation["title"].replace(" ", "_").replace("/", "-")
    return {
        "html": html,
        "filename": f"{safe_title}.html"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)