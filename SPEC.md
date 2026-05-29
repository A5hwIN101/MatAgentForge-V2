# MatAgent-Critique Spec

## 1. Architecture Diagram

```text
+---------------------------+            +----------------------------------+
| React Frontend            |            | FastAPI Backend                  |
|                           |            |                                  |
|  Sidebar                  |            |  REST Endpoints                  |
|  - chat list              | <------->  |  - chats                         |
|  - new chat               |   JSON     |  - materials                     |
|                           |            |  - feedback                      |
|  Main Chat                |            |                                  |
|  - message timeline       | <------->  |  SSE Stream Endpoint             |
|  - streamed status text   | event-src  |  - step events                   |
|  - critique card          |            |  - streamed agent text           |
|  - feedback actions       |            |  - final critique payload        |
+-------------+-------------+            +----------------+-----------------+
              |                                           |
              |                                           |
              v                                           v
    +----------------------+                 +-------------------------------+
    | Local UI State       |                 | Application Services          |
    | - active chat        |                 | - Chat service                |
    | - stream buffer      |                 | - Material screening service  |
    | - unsent drafts      |                 | - Feedback service            |
    +----------------------+                 | - Retraining trigger service  |
                                             +---------------+---------------+
                                                             |
                                                             v
                              +-----------------------------------------------------------+
                              | LangGraph Orchestrator                                     |
                              | - Rule loading                                             |
                              | - Candidate analysis                                       |
                              | - Rule verification                                        |
                              | - Contradiction detection                                  |
                              | - Critique generation                                      |
                              | - Suggestion engine                                        |
                              +-------------------+-------------------+-------------------+
                                                  |                   |
                                                  v                   v
                                     +--------------------+   +----------------------+
                                     | Chroma Vector DB   |   | Groq LLM             |
                                     | - rules embeddings |   | - critique text      |
                                     | - retrieval        |   | - suggestion text    |
                                     +--------------------+   +----------------------+
                                                  |
                                                  v
                                     +-----------------------------+
                                     | SQLite                      |
                                     | - chats                     |
                                     | - chat_items                |
                                     | - materials                 |
                                     | - critiques                 |
                                     | - feedback                  |
                                     | - retraining_events         |
                                     +-----------------------------+
```

## 2. User Flow

1. User opens app and sees sidebar with past chats and a `New Chat` action.
2. User selects an existing chat or starts a fresh one.
3. User enters a material formula such as `LiCoO2`.
4. Frontend creates or reuses the current chat, appends the user message locally, and opens an SSE request to start screening.
5. Backend emits ordered progress events:
   - `Loading domain rules...`
   - `Screening LiCoO2...`
   - `Running critique...`
   - streamed critique text for narrative explanation
   - `Done`
6. Frontend renders step status inline in the chat timeline while preserving optimistic local state.
7. Backend emits the final critique payload.
8. Frontend renders the critique card with summary, flags, suggestions, and action buttons.
9. User clicks:
   - `APPROVE`: store positive feedback and show prompt to analyze next material.
   - `REJECT`: open inline text input, then store structured rejection reason.
   - `MODIFY`: open inline text input, then store requested changes.
10. Feedback is written to SQLite, linked to the critique snapshot and ruleset/model versions.
11. A retraining trigger service records an aggregation event for later rule and prompt improvement.
12. Sidebar updates chat preview with the latest material, verdict badge, and timestamp.

## 3. Frontend Structure

### Primary Component Tree

```text
App
|- ChatLayout
|  |- Sidebar
|  |  |- NewChatButton
|  |  `- ChatHistoryList
|  |     `- ChatHistoryItem
|  `- ChatInterface
|     |- ChatHeader
|     |- MessageList
|     |  |- UserMessage
|     |  |- AgentStatusStream
|     |  |- AgentTextStream
|     |  `- CritiqueCard
|     |     |- ScoreSummary
|     |     |- FlagsSection
|     |     |- SuggestionsSection
|     |     |- TraceDrawer
|     |     `- FeedbackActions
|     `- InputBox
```

### Frontend Responsibilities

- `ChatLayout`
  - Owns page layout and active chat selection.
- `Sidebar`
  - Loads chat history previews.
  - Supports reopen and new chat creation.
- `ChatInterface`
  - Binds active chat to message timeline.
  - Manages stream lifecycle and draft state.
- `AgentStatusStream`
  - Shows step-by-step progress labels.
- `AgentTextStream`
  - Streams narrative response text separate from the structured card.
- `CritiqueCard`
  - Renders a typed top summary plus flexible lower sections.
- `TraceDrawer`
  - Expandable panel for evidence, rule trace, contradiction notes, and citations.
- `FeedbackActions`
  - Handles approve/reject/modify actions and inline reason capture.
- `InputBox`
  - Supports material formula entry and disables while a run is active.

### Frontend State Strategy

- Source of truth:
  - Backend for persisted chats, critiques, and feedback.
- Local UI state:
  - active chat metadata
  - optimistic user message
  - step events buffer
  - streamed explanation text
  - unsent draft input
  - feedback form state
- Recovery behavior:
  - reload persisted history on chat open
  - keep draft and current stream state in memory
  - optional local storage for draft text and last opened chat id

## 4. Backend Structure

### FastAPI Endpoints

- `POST /api/chats`
  - Create a new chat thread.
- `GET /api/chats`
  - Return sidebar chat history with preview fields.
- `GET /api/chats/{chat_id}`
  - Return full timeline for one chat.
- `POST /api/chats/{chat_id}/messages`
  - Persist a user message if needed outside the screening flow.
- `POST /api/chats/{chat_id}/screen`
  - Start a screening run for a material and return SSE stream.
- `POST /api/critiques/{critique_id}/feedback`
  - Store approve/reject/modify feedback with optional text.
- `GET /api/materials/{material_id}`
  - Return stored material and its prior critiques.
- `GET /health`
  - Liveness/readiness check.

### SSE Event Model

- `chat.created`
- `screen.started`
- `step.started`
- `step.updated`
- `text.delta`
- `trace.delta`
- `critique.ready`
- `feedback.saved`
- `screen.completed`
- `screen.failed`

### Recommended SSE Payload Shape

```json
{
  "event": "step.updated",
  "chat_id": "chat_123",
  "run_id": "run_456",
  "timestamp": "2026-05-28T12:00:00Z",
  "data": {
    "step": "critique_generation",
    "label": "Running critique...",
    "status": "in_progress",
    "meta": {
      "material_formula": "LiCoO2",
      "rules_loaded": 24,
      "contradictions_found": 1
    }
  }
}
```

### LangGraph Nodes

1. `load_domain_rules`
   - Retrieves rule packs from Chroma and static rule metadata.
2. `candidate_analysis`
   - Normalizes formula and gathers candidate-specific material context.
3. `rule_verification`
   - Checks retrieved domain rules against candidate evidence.
4. `contradiction_detection`
   - Finds conflicts across retrieved facts, rules, and generated claims.
5. `critique_generation`
   - Produces verdict, score rationale, flags, and explanation text.
6. `suggestion_engine`
   - Produces actionable improvement directions.
7. `finalize_critique`
   - Assembles final structured payload and persists output.

### Streaming Logic

1. Accept `chat_id` and formula input.
2. Create a screening run record.
3. Emit `screen.started`.
4. For each LangGraph node:
   - emit `step.started`
   - perform work
   - emit `step.updated` with metadata
5. During `critique_generation`, stream explanation text via `text.delta`.
6. Persist material, critique, and trace snapshot.
7. Emit `critique.ready` with card payload.
8. Emit `screen.completed`.
9. On failure, emit `screen.failed` with recoverable error details and persist run status.

## 5. Data Flow

```text
Material input
  -> chat screen request
  -> LangGraph run
  -> progress SSE events
  -> critique persisted
  -> critique card rendered
  -> user action (approve/reject/modify)
  -> feedback record persisted
  -> retraining event logged
  -> offline aggregation job reviews feedback patterns
  -> updated ruleset / prompt candidates prepared for human review
```

### Retraining Trigger Path

- Feedback save writes to `feedback`.
- Service creates a `retraining_events` row with:
  - feedback id
  - critique id
  - action type
  - status `pending`
- A scheduled job or admin-triggered workflow aggregates:
  - repeated rejection reasons
  - requested modifications by rule family
  - score/verdict disagreement clusters
- Output of aggregation feeds:
  - rule revision backlog
  - prompt tuning backlog
  - evaluation dataset generation

## 6. Database Schemas

Moderate normalization is the target: stable relational entities, with JSON for evolving trace payloads and flexible critique sections.

### `chats`

| column | type | notes |
|---|---|---|
| id | text pk | `chat_*` |
| title | text | derived from first material, editable later if desired |
| last_material_formula | text | for sidebar preview |
| last_verdict | text | for sidebar badge |
| status | text | `active`, `archived` |
| created_at | datetime | |
| updated_at | datetime | |

### `chat_items`

Stores the timeline for a chat, including user messages, system stream summaries, and critique entries.

| column | type | notes |
|---|---|---|
| id | text pk | `item_*` |
| chat_id | text fk | references `chats.id` |
| item_type | text | `user_message`, `status_stream`, `agent_text`, `critique_card` |
| role | text | `user`, `assistant`, `system` |
| content_text | text | plain text when applicable |
| content_json | json | structured payload for critique/status/trace |
| sequence_no | integer | timeline ordering |
| created_at | datetime | |

### `materials`

| column | type | notes |
|---|---|---|
| id | text pk | `mat_*` |
| formula | text | normalized canonical formula |
| display_formula | text | preserves user-facing formatting |
| source_context_json | json | retrieved source summary |
| created_at | datetime | |
| updated_at | datetime | |

### `critiques`

| column | type | notes |
|---|---|---|
| id | text pk | `crit_*` |
| chat_id | text fk | references `chats.id` |
| chat_item_id | text fk | references `chat_items.id` |
| material_id | text fk | references `materials.id` |
| run_id | text | screening run identifier |
| rules_passed | integer | |
| rules_total | integer | |
| critique_score | real | 0-10 |
| verdict | text | short product-facing summary |
| summary_json | json | typed top summary fields |
| sections_json | json | flags, suggestions, optional citations |
| trace_json | json | expandable evidence/trace payload |
| model_name | text | Groq model used |
| prompt_version | text | prompt version tag |
| ruleset_version | text | rule package version |
| created_at | datetime | |

### `feedback`

| column | type | notes |
|---|---|---|
| id | text pk | `fb_*` |
| critique_id | text fk | references `critiques.id` |
| chat_id | text fk | references `chats.id` |
| material_id | text fk | references `materials.id` |
| action | text | `approve`, `reject`, `modify` |
| reason_text | text | required for reject/modify, optional for approve |
| requested_changes_json | json | parsed structured edits if available |
| critique_snapshot_json | json | stored training-safe snapshot |
| model_name | text | copied from critique |
| prompt_version | text | copied from critique |
| ruleset_version | text | copied from critique |
| user_session_id | text | optional anonymous analytics key |
| created_at | datetime | |

### `retraining_events`

| column | type | notes |
|---|---|---|
| id | text pk | `rt_*` |
| feedback_id | text fk | references `feedback.id` |
| critique_id | text fk | references `critiques.id` |
| event_type | text | `feedback_ingested`, `aggregate_candidate` |
| status | text | `pending`, `processed`, `ignored` |
| notes_json | json | aggregation metadata |
| created_at | datetime | |
| processed_at | datetime | nullable |

## 7. Component Props

### `ChatInterface`

```ts
type ChatInterfaceProps = {
  activeChatId: string | null;
  chatItems: ChatItemViewModel[];
  isLoadingHistory: boolean;
  isStreaming: boolean;
  streamSteps: StreamStepViewModel[];
  streamText: string;
  draftValue: string;
  onDraftChange: (value: string) => void;
  onSubmitMaterial: (formula: string) => Promise<void>;
  onApprove: (critiqueId: string) => Promise<void>;
  onReject: (critiqueId: string, reason: string) => Promise<void>;
  onModify: (critiqueId: string, changeRequest: string) => Promise<void>;
  onOpenTrace: (critiqueId: string) => void;
};
```

### `Sidebar`

```ts
type SidebarProps = {
  chats: ChatHistoryItemViewModel[];
  activeChatId: string | null;
  isLoading: boolean;
  onSelectChat: (chatId: string) => void;
  onCreateChat: () => Promise<void>;
};
```

### `CritiqueCard`

```ts
type CritiqueCardProps = {
  critiqueId: string;
  material: {
    formula: string;
    displayFormula: string;
  };
  summary: {
    rulesPassed: number;
    rulesTotal: number;
    critiqueScore: number;
    verdict: string;
  };
  sections: {
    flags: Array<{ kind: "warning" | "success" | "info"; label: string; detail?: string }>;
    suggestions: Array<{ label: string; detail?: string }>;
    citations?: Array<{ label: string; source: string }>;
  };
  tracePreview?: {
    contradictionCount: number;
    evidenceCount: number;
  };
  isSubmittingFeedback: boolean;
  onApprove: () => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  onModify: (changeRequest: string) => Promise<void>;
  onToggleTrace: () => void;
};
```

### `InputBox`

```ts
type InputBoxProps = {
  value: string;
  disabled: boolean;
  placeholder?: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
};
```

### `ChatHistoryItem`

```ts
type ChatHistoryItemProps = {
  chatId: string;
  title: string;
  lastMaterialFormula?: string;
  lastVerdict?: string;
  updatedAtLabel: string;
  isActive: boolean;
  onClick: () => void;
};
```

## 8. API Contracts

### `POST /api/chats`

Request:

```json
{}
```

Response:

```json
{
  "id": "chat_123",
  "title": "New chat",
  "status": "active",
  "created_at": "2026-05-28T12:00:00Z",
  "updated_at": "2026-05-28T12:00:00Z"
}
```

### `GET /api/chats`

Response:

```json
[
  {
    "id": "chat_123",
    "title": "LiCoO2 screening",
    "last_material_formula": "LiCoO2",
    "last_verdict": "Feasible with concerns",
    "updated_at": "2026-05-28T12:10:00Z"
  }
]
```

### `GET /api/chats/{chat_id}`

Response:

```json
{
  "chat": {
    "id": "chat_123",
    "title": "LiCoO2 screening"
  },
  "items": []
}
```

### `POST /api/chats/{chat_id}/screen`

Request:

```json
{
  "formula": "LiCoO2"
}
```

Response:

- `200 text/event-stream`
- emits status, text, trace, and final critique events

### `POST /api/critiques/{critique_id}/feedback`

Request:

```json
{
  "action": "modify",
  "reason_text": "Add stricter thermal safety constraints."
}
```

Response:

```json
{
  "id": "fb_123",
  "status": "saved"
}
```

## 9. Chunk-by-Chunk Breakdown

All chunks are independently testable and targeted to stay under one day.

### Chunk 1: Project Skeleton and Shared Types

- What
  - Create frontend and backend app skeletons.
  - Define shared DTOs for chats, critique cards, SSE events, and feedback.
- Why
  - Establish a stable contract before UI and API diverge.
- Likely files
  - `frontend/src/types/*`
  - `frontend/src/components/*`
  - `backend/app/schemas/*`
  - `backend/app/main.py`
- Test
  - Typecheck shared models.
  - Backend starts and returns `GET /health`.
- Time
  - `0.5-1 day`

### Chunk 2: Chat and Sidebar Persistence

- What
  - Implement chat creation, chat list, chat detail loading, and sidebar previews.
- Why
  - Users need a persistent thread model before screening.
- Likely files
  - `frontend/src/features/chat/*`
  - `backend/app/routes/chats.py`
  - `backend/app/services/chat_service.py`
  - `backend/app/db/models.py`
- Test
  - Create chat, reload page, reopen chat from sidebar.
- Time
  - `0.5-1 day`

### Chunk 3: Streaming Screening Endpoint

- What
  - Build `POST /api/chats/{chat_id}/screen` with mocked SSE step events and streamed explanation text.
- Why
  - De-risks the hardest UX path early.
- Likely files
  - `frontend/src/features/screening/*`
  - `backend/app/routes/screen.py`
  - `backend/app/streaming/sse.py`
- Test
  - Submit `LiCoO2`, observe ordered step updates and text stream in UI.
- Time
  - `1 day`

### Chunk 4: Critique Card Rendering

- What
  - Render final structured card with summary, flags, suggestions, and trace drawer.
- Why
  - This is the product’s primary decision surface.
- Likely files
  - `frontend/src/components/CritiqueCard.tsx`
  - `frontend/src/components/TraceDrawer.tsx`
  - `frontend/src/styles/*`
- Test
  - Feed fixture payloads and visually verify 10-second scannability.
- Time
  - `0.5-1 day`

### Chunk 5: LangGraph Orchestration Integration

- What
  - Replace mocked screening steps with real LangGraph nodes and structured persistence.
- Why
  - Connect product UX to actual domain intelligence.
- Likely files
  - `backend/app/graph/nodes/*`
  - `backend/app/graph/workflow.py`
  - `backend/app/services/screening_service.py`
- Test
  - Run one material end-to-end and verify all node outputs persist.
- Time
  - `1 day`

### Chunk 6: Feedback Capture and Storage

- What
  - Implement approve/reject/modify flows, inline reason input, and feedback persistence.
- Why
  - Feedback loop is the product’s improvement engine.
- Likely files
  - `frontend/src/components/FeedbackActions.tsx`
  - `backend/app/routes/feedback.py`
  - `backend/app/services/feedback_service.py`
- Test
  - Save each action type and verify SQLite rows + UI confirmation.
- Time
  - `0.5 day`

### Chunk 7: Retraining Event Pipeline

- What
  - Add retraining event creation and a basic aggregation job scaffold.
- Why
  - Makes feedback operational rather than passive.
- Likely files
  - `backend/app/services/retraining_service.py`
  - `backend/app/jobs/aggregate_feedback.py`
- Test
  - Feedback insert creates pending retraining event.
- Time
  - `0.5 day`

### Chunk 8: Polish, Failure States, and Trace UX

- What
  - Add empty states, loading states, error recovery, and trace drawer details.
- Why
  - Makes the app usable in real lab workflows.
- Likely files
  - `frontend/src/features/*`
  - `backend/app/error_handlers.py`
- Test
  - Simulate stream failure, retry, empty history, and long-running critique.
- Time
  - `0.5-1 day`

## 10. Recommended Folder Structure

```text
matagent-critique/
├─ frontend/
│  ├─ src/
│  │  ├─ app/
│  │  ├─ components/
│  │  ├─ features/
│  │  │  ├─ chat/
│  │  │  ├─ screening/
│  │  │  └─ feedback/
│  │  ├─ hooks/
│  │  ├─ lib/
│  │  ├─ styles/
│  │  └─ types/
├─ backend/
│  ├─ app/
│  │  ├─ routes/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  ├─ graph/
│  │  │  ├─ nodes/
│  │  │  └─ workflow.py
│  │  ├─ streaming/
│  │  ├─ db/
│  │  ├─ jobs/
│  │  └─ main.py
│  └─ tests/
├─ data/
│  ├─ sqlite/
│  └─ chroma/
└─ SPEC.md
```

## 11. Implementation Notes

- Use SSE for progress and streamed explanation text; do not use WebSockets unless product requirements expand to collaborative or live co-editing behavior.
- Keep the card’s top summary strongly typed and compact for the 10-second scan goal.
- Store evolving lower card sections and trace payloads as JSON to avoid premature schema churn.
- Capture critique snapshots in feedback rows so later analysis remains stable even if prompts or rules change.
- Treat retraining as an offline, reviewable workflow instead of immediate autonomous rule mutation.

## 12. Open Assumptions

- One authenticated user model is not yet defined; this spec assumes either anonymous lab sessions or a single-tenant internal app.
- Formula normalization rules are not yet finalized; backend should preserve both raw input and normalized display forms.
- Chroma collections and Materials Project / ICSD ingestion pipelines are assumed to exist or be handled in a separate ingestion spec.
