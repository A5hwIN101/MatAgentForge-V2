# MatAgent-Critique: Architecture & Development Progress

## Project Overview
- **Name:** MatAgent-Critique
- **Purpose:** AI-powered battery materials screening agent with human-in-the-loop feedback
- **Architecture:** Chat interface (React) + LangGraph pipeline (FastAPI) + Groq LLM + pre-trained rules engine
- **Target:** Demo day June 4, 2026, 7pm ET
- **Current Status:** arXiv scraper, rule extraction, citation integration, and live citation-backed critique payloads are COMPLETE. Current working state is ready for commit, multi-material verification, and deployment testing.

---

## COMPLETED WORK

### Chunk 1: Project Skeleton [COMPLETE]
- **What:** Next.js + FastAPI boilerplate, shared types, health endpoint
- **Files:** Type definitions (TS + Pydantic), folder structure, requirements.txt
- **Status:** Verified working

### Chunk 2: Chat Persistence [COMPLETE]
- **What:** SQLite DB (chats, chat_items, materials, critiques, feedback tables), CRUD service
- **Features:** Create chat, list chats, get chat detail, update chat title
- **API Routes:** POST/GET/PUT /api/chats
- **Status:** All operations tested via curl, verified

### Chunk 3, Bucket 1: SSE Streaming Endpoint [COMPLETE]
- **What:** POST /api/chats/{chat_id}/screen returns Server-Sent Events stream
- **Features:** Mocked step events, word-by-word text streaming
- **Files:** screen.py, sse.py
- **Status:** Streaming verified

### Chunk 3, Bucket 2: Critique Card Component [COMPLETE]
- **What:** React CritiqueCard.tsx displays verdict, score, flags, suggestions, trace details
- **Features:** TraceDrawer.tsx (expandable rule/contradiction details), useScreening.ts hook
- **Status:** Render path verified

### Chunk 3, Bucket 3: Chat Layout [COMPLETE]
- **What:** Full chat UI with sidebar + message timeline + input box
- **Components:** ChatLayout, Sidebar, MessageList, InputBox
- **Hooks:** useChat (fetches chats, manages active chat), useScreening (SSE streaming)
- **Status:** Layout renders, responsive, dark mode

### Chunk 3, Bucket 4: LangGraph + Groq Integration [COMPLETE]
- **What:** Real end-to-end pipeline: formula -> rules -> critique -> explanation
- **LangGraph Nodes:**
  1. load_domain_rules_node -> loads 15 domain rules from JSON
  2. candidate_analysis_node -> parses formula (e.g., LiCoO2 -> Li, Co, O)
  3. rule_verification_node -> Groq checks rule violations
  4. contradiction_detection_node -> Groq finds rule conflicts
  5. critique_generation_node -> Groq writes explanation (streamed)
  6. finalize_critique_node -> assembles CritiqueCard payload
- **Groq Config:** Live screening uses a supported Groq text model. Rule verification prompts were trimmed to stay under Groq TPM limits once citation-rich rules were added.
- **SSE Events:** screen.started, step.started, step.updated, text.delta, critique.ready, screen.completed
- **Backend:** GROQ_API_KEY loads from environment and BOM-safe `.env` fallback logic
- **Frontend:** Wired to http://localhost:8000 (real backend, not mocks)
- **Latest Verified Result:** LiCoO2 -> verdict=feasible, score=1.0, critique.ready reached, rules_matched included cited rules
- **Status:** VERIFIED WORKING END-TO-END

### Chunk 3, Bucket 5: Feedback Capture [COMPLETE]
- **What:** Users click APPROVE/REJECT/MODIFY buttons, feedback stored in SQLite
- **Frontend:** FeedbackActions.tsx (3 buttons, inline text input for REJECT/MODIFY)
- **Backend:** POST /api/critiques/{critique_id}/feedback endpoint
- **Storage:** SQLite feedback table (id, critique_id, action, reason_text, created_at)
- **Integration:** Buttons render below CritiqueCard in MessageList
- **Status:** Fully wired and previously verified against SQLite persistence

### Chunk 4: arXiv Rule Injection + Citations [COMPLETE]
- **What:** Added lightweight arXiv scraping, citation-aware rule extraction, and frontend citation rendering
- **Rules:** 12 new extracted rules merged with the existing 3 -> 15 total rules
- **Citations:** Extracted rules now carry citation metadata and the backend includes them in `critique.ready` under `trace.citations`
- **Frontend:** TraceDrawer now renders clickable arXiv links below matched domain rules
- **Status:** Verified with live LiCoO2 payload containing citations

---

## CRITICAL FINDING: Rules Are Still Domain-Light [WARNING]

### The Issue
Tested with NaCl:
- **MatAgent verdict:** "Feasible battery material (score 1.0)"
- **Reality (Gemini):** "NaCl is insulator, not viable active electrode"
- **Root cause:** Current 15 rules still emphasize structural and high-level materials signals more than full electrochemistry:
  - [YES] Charge neutrality
  - [YES] Oxidation states
  - [YES] Stoichiometry
  - [PARTIAL] Ionic transport and related literature-backed heuristics
  - [NO] Full electrochemical coverage for band gaps, voltage windows, and lifecycle behavior

### What Rules Check Now
- Chemical stability (charge balance, oxidation states)
- Basic thermodynamic viability
- Early literature-backed screening signals with citations
- **NOT YET:** Full real-world battery performance coverage across all candidate classes

### Impact for Demo
- [YES] System architecture proven
- [YES] Citation-backed rules improve credibility
- [WARNING] Some extracted rules are generic, but they are accepted for demo stability right now
- [NO] The system should still be demoed with known battery-relevant materials instead of arbitrary compounds

---

## RULE STATUS

### Current Rule Set
1. Existing baseline rules: 3
2. New extracted rules: 12
3. Total active rules: 15

### Citation Support
- Extracted rules include `citations` metadata with arXiv id, paper title, authors, year, and URL
- Backend final critique payload includes citations in `trace.citations`
- Frontend renders those citations as clickable arXiv links in the Trace drawer

---

## TECHNOLOGY STACK (Confirmed Working)

**Frontend:**
- Next.js 16, React 18, TypeScript, Tailwind CSS
- SSE streaming, real-time chat UI

**Backend:**
- FastAPI, LangGraph 0.6.11, Groq API, pymatgen
- SQLAlchemy 2.0.41, SQLite

**LLM:**
- Groq
- `llama-3.2-90b-vision-preview` is decommissioned
- Rule extractor tries that model first, then falls back to a live Groq model
- Live screening path uses a supported text model

**Database:**
- SQLite (dev), PostgreSQL (prod target)
- 5 tables: chats, chat_items, materials, critiques, feedback

**Deployment:**
- Frontend: pending Vercel deploy
- Backend: pending Railway deploy

---

## KEY FILES (Current)

### Backend
- `app/main.py` - FastAPI app, loads `.env`, includes routers (health, chats, screen, feedback)
- `app/graph/workflow.py` - LangGraph StateGraph, 6 nodes, BOM-safe Groq key loading, trimmed verification prompts, citation-aware final payload
- `app/graph/state.py` - CritiqueState TypedDict
- `app/routes/screen.py` - POST /api/chats/{chat_id}/screen (SSE endpoint)
- `app/routes/feedback.py` - POST /api/critiques/{critique_id}/feedback (feedback storage)
- `app/services/chat_service.py` - Chat CRUD logic
- `app/db/models.py` - SQLAlchemy models (5 tables)
- `scraper_arxiv.py` - standalone arXiv scraper for materials papers
- `rule_extractor_simple.py` - standalone Groq-backed rule extractor with citation merge
- `rules/extracted_rules.json` - 15 total rules with citation support
- `app/schemas/critique.py` - citation-aware critique payload schema

### Frontend
- `features/chat/ChatLayout.tsx` - Main layout (sidebar + message timeline)
- `features/chat/Sidebar.tsx` - Chat history, New Chat button
- `features/chat/MessageList.tsx` - Renders messages by type, includes CritiqueCard + FeedbackActions
- `features/chat/InputBox.tsx` - Formula input + Analyze button
- `components/CritiqueCard.tsx` - Critique display (verdict, score, flags, suggestions)
- `components/TraceDrawer.tsx` - Expandable rule/contradiction details with clickable arXiv links
- `features/feedback/FeedbackActions.tsx` - APPROVE/REJECT/MODIFY buttons
- `hooks/useChat.ts` - Fetch chats, manage active chat (real backend)
- `hooks/useScreening.ts` - SSE streaming, build critique from real response
- `types/critique.ts` - frontend citation types for `trace.citations`

### Key Changed Files in Latest Pass
- `backend/scraper_arxiv.py`
- `backend/rule_extractor_simple.py`
- `backend/rules/extracted_rules.json`
- `backend/app/graph/workflow.py`
- `backend/app/schemas/critique.py`
- `frontend/src/types/critique.ts`
- `frontend/src/components/TraceDrawer.tsx`

---

## VERIFIED WORKFLOWS

### Full End-to-End Screening
1. [YES] User types formula (LiCoO2)
2. [YES] Frontend sends to backend: POST /api/chats/{id}/screen
3. [YES] Backend loads 15 rules
4. [YES] LangGraph processes all 6 nodes
5. [YES] Groq generates explanation (streaming)
6. [YES] SSE events stream to frontend
7. [YES] CritiqueCard renders
8. [YES] critique.ready includes `trace.citations`
9. [YES] Cited rules appear in `rules_matched`
10. [YES] Trace drawer can render clickable arXiv links

### Feedback Workflow
1. [YES] User clicks feedback button (APPROVE/REJECT/MODIFY)
2. [YES] Feedback sent to backend
3. [YES] SQLite stores feedback row
4. [YES] "Feedback saved" confirmation appears

### Latest Verified Test
- Backend health: [YES] http://127.0.0.1:8000/health
- Frontend loads: [YES] http://localhost:3000
- Material: [YES] LiCoO2
- Verdict: [YES] feasible
- Domain rules total: [YES] 15
- critique.ready reached: [YES]
- trace.citations count: [YES] 3
- cited rules shown in rules_matched: [YES]
- citations render in Trace drawer as clickable arXiv links: [YES]

---

## KNOWN ISSUES & LIMITATIONS

### Issue 1: Streaming UX (Bucket 6 - Polish)
- SSE events are emitted correctly
- UI can still batch visible updates instead of feeling fully step-by-step
- Expected: Each step appears progressively
- Current: Streaming text is live, but step pacing can still feel compressed
- Fix: Refine frontend event rendering for clearer progressive status display

### Issue 2: Extracted Rule Quality
- 12 extracted rules were successfully merged
- Some of the extracted rules are generic rather than sharply electrochemistry-specific
- This is acceptable for demo stability right now
- No post-filtering pass is being added yet

### Issue 3: Groq Model/Rate-Limit Constraints
- `llama-3.2-90b-vision-preview` is decommissioned
- Extractor falls back to a supported Groq model
- Large rule payloads originally pushed screening into TPM limits
- Verification prompts were trimmed to keep screening viable once citations were attached

### Issue 4: Deployment Still Pending
- Local frontend and backend work
- Production deployment has not been completed yet

---

## TESTING CHECKLIST

- [x] Backend /health endpoint
- [x] Chat CRUD (create, list, get, update)
- [x] SSE streaming (real, not mocked)
- [x] Frontend chat layout renders
- [x] Groq API integration (supported model path works)
- [x] Real critique generation (LLM writes explanation)
- [x] Text streaming (word-by-word)
- [x] arXiv scraper fetches 30 papers
- [x] 12 new rules extracted and merged with existing 3
- [x] Rules stored with citation metadata
- [x] critique.ready includes trace.citations
- [x] Trace drawer renders clickable arXiv links
- [x] Feedback buttons render below critique
- [x] Feedback storage (SQLite verified)
- [x] Feedback success message ("Feedback saved")
- [ ] Streaming UX polish
- [ ] Multi-material live verification (LiCoO2, LiFePO4, NMC)
- [ ] Deployment to Vercel + Railway

---

## NEXT IMMEDIATE STEPS

1. **Commit and push the current working state**
2. **Test 3 materials live**
   - LiCoO2
   - LiFePO4
   - NMC
3. **Record verdict + citation count for each**
4. **Click feedback buttons for each**
5. **Deploy frontend to Vercel and backend to Railway if tests pass**

---

## BUCKET BREAKDOWN

## Chunk 3, Bucket 6: Error Handling & UI Polish

### Bucket 3.6.0: Viewport & Scroll Stability
* Make app shell fit full viewport height [done]
* Prevent whole-page endless scrolling [done]
* Make sidebar independently scrollable [done]
* Make main message area independently scrollable [done]
* Keep input box visible at the bottom of the chat shell [done]
* Auto-scroll to newest streaming result [done]
* Cap Trace drawer height and keep citations clickable [done]

### Bucket 3.6.1: Error States
* Implement error boundary in MessageList [to be done]
* Display error message when screen.failed received [done]
* Show retry button on error [to be done]
* Log errors to console [to be done]
* Suppress critique/feedback UI for invalid formula results [done]

### Bucket 3.6.2: Loading States
* Add loading spinner during screening [to be done]
* Show spinner before steps appear [to be done]
* Disable input during screening [done]
* Show "Analyzing..." text [done]
* Add skeleton loaders for chat items [to be done]

### Bucket 3.6.3: Empty States
* Show placeholder when no chats exist [to be done]
* Message: "No chats yet. Click 'New Chat' to start." [to be done]
* Show placeholder when chat is empty [to be done]
* Message: "Enter a material formula and click Analyze" [to be done]

### Bucket 3.6.4: Streaming UX Polish
* Update MessageList to render steps one-by-one [to be done]
* Each step.updated renders immediately [to be done]
* Wait 0.5s before next step [to be done]
* Create smooth fade-in animation [to be done]

### Bucket 3.6.5: Responsive Design
* Test layout on mobile (narrow viewport) [to be done]
* Adjust sidebar collapse on mobile [to be done]
* Test input/button touch targets [to be done]

---

## Chunk 4: ArXiv Scraper & Rule Extraction

### Bucket 4.1: ArXiv Scraper
* Create backend/scraper_arxiv.py [done]
* Fetch papers from arxiv.org/api/query [done]
* Query: "battery materials" + domain keywords (ionic conductivity, band gap, cycle life, voltage stability) [done]
* Limit: 30 papers [done]
* Extract: arxiv_id, title, authors, publication_year, url, abstract [done]
* Store to backend/data/arxiv_papers.json [done]

### Bucket 4.2: Rule Extraction from Papers
* Create backend/rule_extractor_simple.py [done]
* For each paper abstract, call Groq: "Extract 1-2 quantitative battery rules" [done]
* Output format: {rule_text, threshold_value, threshold_unit, domain, evidence_from_paper} [done]
* Link each rule to source paper (citations array) [done]
* Store extracted rules temporarily [done]

### Bucket 4.3: Rule Schema Update
* Update rules/extracted_rules.json schema [done]
* Add `threshold_value` (numeric or null) [done]
* Add `threshold_unit` (string or null) [done]
* Add `citations` (array of {arxiv_id, paper_title, authors, year, url}) [done]
* Add `domain` (string) [done]
* Add `evidence_from_paper` (string) [done]
* Add `severity` (warning|success) [done]

### Bucket 4.4: Rule Merging & Storage
* Merge new extracted rules with existing 3 rules [done]
* Total rules: 15 [done]
* Validate JSON schema [done]
* Store in backend/rules/extracted_rules.json [done]

### Bucket 4.5: Backend Citation Integration
* Update workflow.py finalize_critique_node [done]
* Include citations in critique.ready payload [done]
* Pass trace.citations to frontend [done]

### Bucket 4.6: Frontend Citation Display
* Update TraceDrawer.tsx [done]
* Display citations under matched rules [done]
* Format: "Rule Name - Paper Title (Authors, Year)" [done]
* Make citations clickable: href="https://arxiv.org/abs/..." [done]

### Bucket 4.7: Testing & Verification
* Papers fetched: 30 [done]
* New rules extracted: 12 [done]
* Total rules merged: 15 [done]
* Test LiCoO2 verdict: feasible [done]
* Test LiCoO2 rules_matched includes cited rules [done]
* Test LiCoO2 citations_count: 3 [done]
* Backend tests still pass (6 passed) [done]
* Frontend lint passes [done]
* Frontend build passes [done]

---

## Chunk 5: Deployment

### Bucket 5.1: GitHub Preparation
* Ensure all code committed [in progress]
* Last commit target: "feat: arxiv scraper + 15 rules with citations" [in progress]
* Verify .gitignore includes .env [done]
* Push to main branch [to be done]

### Bucket 5.2: Frontend Deployment (Vercel)
* Install Vercel CLI [to be done]
* Connect MatAgentForge GitHub repo to Vercel [to be done]
* Set environment variables (if needed) [to be done]
* Deploy via `vercel deploy` [to be done]
* Verify frontend live URL works [to be done]
* Update backend URL in frontend (from localhost:8000 to live Railway URL) [to be done]

### Bucket 5.3: Backend Deployment (Railway)
* Create Railway account [to be done]
* Connect MatAgentForge GitHub repo [to be done]
* Set environment variable: GROQ_API_KEY [to be done]
* Set environment variable: DATABASE_URL (if not SQLite) [to be done]
* Deploy [to be done]
* Verify backend health check works (/health endpoint) [to be done]
* Get live backend URL [to be done]

### Bucket 5.4: Integration Testing
* Test frontend -> backend (SSE streaming) on live URLs [to be done]
* Test all 3 demo materials: LiCoO2, LiFePO4, NMC [to be done]
* Verify feedback buttons work on live [to be done]

---

## Chunk 6: Pre-Demo Validation

### Bucket 6.1: Material Testing
* Test LiCoO2 expected verdict: feasible [done]
* Test LiCoO2 expected rules matched: 3+ [done]
* Test LiCoO2 expected citations: visible [done]
* Test LiFePO4 expected verdict: feasible [to be done]
* Test LiFePO4 expected rules matched: 3+ [to be done]
* Test LiFePO4 expected contradictions (if any) [to be done]
* Test NMC (Li(Ni,Mn,Co)O2) expected verdict: feasible [to be done]
* Test NMC expected rules matched: 3+ [to be done]
* Test NMC expected citations: visible [to be done]

### Bucket 6.2: Edge Case Testing
* Test invalid formula (e.g., "LiCo02") [done]
* Expected result: error message [done]
* Test empty input [to be done]
* Expected result: validation error or placeholder [to be done]

### Bucket 6.3: Demo Script Preparation
* Write demo walkthrough (step-by-step) [to be done]
* Step 1: Open live URL [to be done]
* Step 2: Type "LiCoO2" [to be done]
* Step 3: Click Analyze [to be done]
* Step 4: Show streaming critique [to be done]
* Step 5: Expand Trace Details [to be done]
* Step 6: Show citations [to be done]
* Step 7: Click APPROVE feedback [to be done]
* Step 8: Show "Feedback saved" [to be done]

### Bucket 6.4: Demo Environment Check
* Verify backend is running (live URL) [to be done]
* Verify frontend is running (live URL) [to be done]
* Verify Groq API key is set [to be done]
* Verify SQLite has chat history [to be done]

---

## Chunk 7: Post-Demo Roadmap (Phase 2)

### Bucket 7.1: UI Streaming Polish (Deferred from Bucket 3.6.4)
* Implement step-by-step rendering (not batch) [deferred]
* Add smooth animations [deferred]

### Bucket 7.2: Extended Rule Mining
* Run full ArXiv scraper (100+ papers) [deferred]
* Extract 50+ domain-specific rules [deferred]
* Add electrochemistry-focused rules [deferred]

### Bucket 7.3: OQMD Integration (Phase 1.5b from old README)
* Integrate OQMD database [deferred]
* Mine structure-stability rules [deferred]

### Bucket 7.4: Retraining Pipeline
* Implement feedback -> rule refinement loop [deferred]
* Log retraining events [deferred]
* Trigger rule updates from feedback [deferred]

### Bucket 7.5: Production Hardening
* Move SQLite -> PostgreSQL [deferred]
* Add request rate limiting [deferred]
* Add request/response logging [deferred]
* Add security headers [deferred]

### Bucket 7.6: CHGNet Integration
* Integrate CHGNet MLIP (replace M3GNet) [deferred]
* Implement structure prediction pipeline [deferred]

### Bucket 7.7: Advanced Features
* Human-in-the-loop dashboard [deferred]
* Batch material screening [deferred]
* Export reports (PDF/CSV) [deferred]

---

## Chunk 8: Long-Term Vision (PBSA Architecture)

### Bucket 8.1: Planning Agent
* Design Planning Agent module [deferred]
* Implement multi-step research planning [deferred]

### Bucket 8.2: Critique & Reflection Agents
* Implement Critique Agent [deferred]
* Implement Reflection Agent [deferred]

### Bucket 8.3: Deep Research Mode
* Implement async deep research pipeline [deferred]
* Allow multi-hour research runs [deferred]

### Bucket 8.4: Rule Engine Expansion
* Unified rule knowledge coordination [deferred]
* Community contribution system [deferred]

---

## Status Summary

**[done] Completed Foundations**
* Full end-to-end system working [done]
* 15 rules with citations [done]
* Feedback loop closed [done]
* Ready for demo-day validation [done]

**[in progress] Deployment**
* Git push [to be done]
* Vercel deployment [to be done]
* Railway deployment [to be done]

**[to be done] Pre-Demo Validation**
* Material testing [to be done]
* Edge case testing [to be done]
* Demo script [to be done]

**[deferred] Post-Demo UX and Phase 2**
* Streaming UX polish deferred due to time pressure [deferred]
* Extended rules, retraining, and production hardening [deferred]

---

## DEPLOYMENT CHECKLIST

- [ ] Current state committed and pushed
- [ ] Frontend tested locally (3000)
- [ ] Backend tested locally (8000)
- [ ] LiCoO2 tested live
- [ ] LiFePO4 tested live
- [ ] NMC tested live
- [ ] Verdict and citation count captured for each
- [ ] Feedback buttons tested for each
- [ ] Vercel deployment complete
- [ ] Railway deployment complete
- [ ] Live URLs tested

---

## LAST UPDATED

**2026-05-31**
- arXiv scraper created and fetched 30 papers
- 12 new rules extracted and merged with the existing 3
- Active rule count updated to 15
- Citations linked to extracted rules and carried through critique.ready as `trace.citations`
- TraceDrawer updated to render clickable arXiv links
- LiCoO2 verified with verdict `feasible`, domain rules total `15`, and `trace.citations` count `3`
