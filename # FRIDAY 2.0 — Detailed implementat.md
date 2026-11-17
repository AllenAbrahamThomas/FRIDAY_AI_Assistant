# **FRIDAY 2.0 — Detailed implementation plan**

My recommendation is to build **FRIDAY 2.0 as an upgrade of your existing FRIDAY_AI_Assistant**, not as a completely new project.

The objective is to turn it into a reliable, local-first AI assistant that can understand a request, plan the work, select tools, retrieve information, verify evidence, remember useful context, and explain what it did.

For the Napster AI Solutions Architect Intern application, the important thing is not to build the largest possible assistant. It is to demonstrate that you can **design an AI system, make sensible architecture decisions, integrate models and tools, evaluate the results, and explain the trade-offs**.

I suggest we follow the phases below. Each phase has a clear objective, implementation tasks, files to create or modify, tests, and an approval checkpoint. We will not move to the next phase until you approve the current one.

## **1. Final product definition**

**FRIDAY 2.0**

Proposed direction

**Local-First Personal AI & Intelligence Platform**

FRIDAY should be able to:

- Understand natural-language requests.
- Decide whether to answer directly or use tools.
- Break complex requests into smaller steps.
- Run specialised agents for research and intelligence tasks.
- Retrieve information from World Monitor and other sources.
- Compare evidence and identify uncertainty.
- Maintain user-controlled persistent memory.
- Explain its actions and show execution details.
- Run primarily on local models through Ollama.

  **Signature capability:** geopolitical and global intelligence research, building on the strongest existing feature of FRIDAY 1.0.

### **Example of the finished experience**

You ask:

> FRIDAY, prepare an intelligence briefing on the latest developments in a region. Include threat levels, recent events, important news, and possible implications.

FRIDAY should:

1. Understand that this is a research and intelligence task.
2. Create a plan.
3. Retrieve relevant World Monitor risk information.
4. Search for recent news.
5. Compare information across sources.
6. Identify conflicting or unverified information.
7. Generate a structured briefing.
8. Include source links and timestamps.
9. Show which tools and agents it used.
10. Record the task in its execution history.

This is the primary demonstration scenario we will build towards.

## **2. Target architecture**

This is the architecture I recommend. It is a target design, not a claim that all these components already exist in your repository.

**FRIDAY User Interface**

Chat · Voice · Intelligence Dashboard · Memory · Execution History

**FastAPI Application Layer**

API routes · Authentication boundary · Request validation

**FRIDAY Core Orchestrator**

Intent · Planning · Agent selection · Tool execution · Result synthesis

**Specialised Agents**

Research · Intelligence · Coding · General assistant

**Model Manager**

Ollama · Model selection · Provider interface

**Tool Registry**

World Monitor · News · Search · Weather

**Memory & Context**

Conversation · Persistent memory · Retrieval

**Observability & Evaluation**

Execution traces · Tool results · Errors · Latency · Quality checks

**Local Infrastructure**

Ollama · Database · Local files · External APIs

### **Main architectural decisions**

| Area                | Proposed choice                                     |
| ------------------- | --------------------------------------------------- |
| Backend             | Keep FastAPI and Python                             |
| Frontend            | Keep React and Vite                                 |
| Local inference     | Ollama                                              |
| Model integration   | Common model-provider interface                     |
| Agent orchestration | Custom, transparent orchestrator                    |
| Data storage        | SQLite initially                                    |
| Semantic memory     | Add a vector store only when needed                 |
| External data       | Existing World Monitor API, news and search         |
| Testing             | Pytest and mocked external services                 |
| Frontend testing    | Existing tooling first; add browser tests if useful |
| Deployment          | Local-first; deployment hardening later             |

**Important:** I do not recommend adding LangChain, LangGraph, multiple databases, Kubernetes, or a complicated microservice setup just to make the architecture look impressive. We should add dependencies only when they solve a real problem.

# **3. Implementation phases**

Estimated effort assumes focused development sessions. Actual duration depends on the baseline audit, bugs, and available time.

## **Phase 0 — Repository audit and stable baseline**



Mandatory first phase

Estimated 0.5–1 day



**Objective:** Establish exactly what works in FRIDAY 1.0 before modifying anything.

### **Tasks**

1. Confirm the repository and current Git branch.
2. Check whether the local working copy matches GitHub.
3. Inspect all backend and frontend dependencies.
4. Verify Python, Node.js, npm, Ollama and GPU availability.
5. Check installed Ollama models and available disk space.
6. Install dependencies according to the repository instructions.
7. Start the backend and frontend independently.
8. Test the existing chat functionality.
9. Test Ollama connectivity.
10. Test World Monitor API connectivity.
11. Test news search and weather.
12. Run the existing test suite.
13. Identify failures caused by network-dependent tests.
14. Record existing bugs and distinguish code defects from environment issues.
15. Create a Git checkpoint before changing the application.

### **Files and areas involved**

- `README.md`
- `backend/requirements.txt`
- `backend/run.py`
- `backend/app/main.py`
- `frontend/package.json`
- `commands.txt`
- Existing test files

### **Completion criteria**

- Backend starts successfully.
- Frontend starts successfully.
- Local model responds to a test prompt.
- Existing World Monitor functionality is tested.
- Current tests and failures are documented.
- A clean rollback point exists in Git.

**Approval checkpoint:** We approve the actual baseline report before changing the architecture.

## **Phase 1 — Clean up and strengthen the existing FRIDAY 1.0**



Preserve existing work

Estimated 1–2 days



**Objective:** Make the existing assistant stable enough to serve as the foundation for 2.0.

### **Tasks**

1. Review backend configuration and remove hardcoded configuration values where practical.
2. Centralise environment variables and provide a safe `.env.example`.
3. Add proper request validation and consistent API error responses.
4. Improve Ollama connection handling:
   - Detect unavailable Ollama.
   - Handle model-not-found errors.
   - Handle timeouts.
   - Return useful error messages.
5. Improve external API handling:
   - Request timeouts.
   - Retry selected transient failures.
   - Handle unavailable APIs.
   - Distinguish live results from fallback data.
6. Fix or clearly label simulated frontend telemetry.
7. Clearly distinguish live World Monitor data from mock data.
8. Restrict CORS to the intended frontend origin.
9. Separate external API logic from the route handlers.
10. Improve test isolation by mocking external API calls.
11. Fix any bugs discovered in Phase 0.
12. Update documentation with accurate installation and run instructions.

### **Expected output**

- More reliable backend.
- More predictable API responses.
- Safer configuration.
- Reproducible tests.
- Accurate application status indicators.

### **Completion criteria**

- Existing chat still works.
- Existing World Monitor features still work.
- API failures are handled without crashing the application.
- Tests can run without depending on live external APIs.
- No existing feature is removed without an explicit reason.

**Approval checkpoint:** You test the cleaned-up application and approve the stable foundation.

## **Phase 2 — Build the FRIDAY core orchestrator**



Highest architectural priority

Estimated 2–3 days



**Objective:** Replace the current fragmented request flow with a single central decision-making system.

This is the most important architectural improvement.

### **2.1 Request lifecycle**

Every user request should pass through a consistent lifecycle:

\#chatgpt-mermaid-\_r_7hq\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_7hq\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_7hq\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_7hq\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_7hq\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_7hq\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_7hq\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_7hq\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_7hq\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_7hq\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7hq\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7hq\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_7hq\_ p{margin:0;}#chatgpt-mermaid-\_r_7hq\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_7hq\_ .label text,#chatgpt-mermaid-\_r_7hq\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ .node rect,#chatgpt-mermaid-\_r_7hq\_ .node circle,#chatgpt-mermaid-\_r_7hq\_ .node ellipse,#chatgpt-mermaid-\_r_7hq\_ .node polygon,#chatgpt-mermaid-\_r_7hq\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .rough-node .label text,#chatgpt-mermaid-\_r_7hq\_ .node .label text,#chatgpt-mermaid-\_r_7hq\_ .image-shape .label,#chatgpt-mermaid-\_r_7hq\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_7hq\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .rough-node .label,#chatgpt-mermaid-\_r_7hq\_ .node .label,#chatgpt-mermaid-\_r_7hq\_ .image-shape .label,#chatgpt-mermaid-\_r_7hq\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_7hq\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_7hq\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7hq\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7hq\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_7hq\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_7hq\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_7hq\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_7hq\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_7hq\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_7hq\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7hq\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_7hq\_ .icon-shape,#chatgpt-mermaid-\_r_7hq\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_7hq\_ .icon-shape p,#chatgpt-mermaid-\_r_7hq\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_7hq\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_7hq\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_7hq\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_7hq\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_7hq\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_7hq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_7hq\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_7hq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_7hq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7hq\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_7hq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7hq\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_7hq\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_7hq\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_7hq\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_7hq\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .node rect,#chatgpt-mermaid-\_r_7hq\_ .node circle,#chatgpt-mermaid-\_r_7hq\_ .node ellipse,#chatgpt-mermaid-\_r_7hq\_ .node polygon,#chatgpt-mermaid-\_r_7hq\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_7hq\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_7hq\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_7hq\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_7hq\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7hq\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}User RequestInput ValidationContext ManagerIntent ClassificationTask TypeDirect Model ResponseResearch AgentIntelligence AgentCoding AgentGeneral AgentTool ExecutionObserve ResultsMore Steps Needed?Update PlanFinal ResponseSave Execution TraceSimple questionResearchWorld IntelligenceCodingGeneral taskYesNo

### **2.2 Components to implement**

**A. Intent classifier**

Determine what the user is asking.

Initial categories:

- `general`
- `research`
- `world_intelligence`
- `coding`
- `weather`
- `memory`
- `task_management`

The classifier should return structured data rather than just a text label.

Example:

```
{
  "intent": "world_intelligence",
  "requires_tools": true,
  "complexity": "multi_step",
  "confidence": 0.92
}
```

This is an illustrative output. The actual implementation should validate the returned structure.

**B. Task planner**

For complex tasks, create an ordered plan.

Example:

```
Task: Prepare an intelligence briefing

1. Retrieve current risk scores.
2. Retrieve recent events.
3. Search for relevant news.
4. Compare the collected information.
5. Generate the briefing.
6. Attach sources and timestamps.
```

**C. Tool registry**

Create a central registry of available tools.

Each tool should have:

- Unique name.
- Description.
- Input schema.
- Execution function.
- Output format.
- Timeout.
- Error handling.

**D. Execution engine**

Responsible for:

- Selecting the correct tool.
- Executing it.
- Collecting results.
- Returning observations to the orchestrator.
- Deciding whether another step is required.

**E. Response synthesiser**

Combines the results into a final answer, without treating tool output as automatically trustworthy.

### **2.3 Suggested new files**

```
backend/app/core/
    orchestrator.py
    planner.py
    intent_classifier.py
    execution_engine.py
    context_manager.py

backend/app/tools/
    base_tool.py
    registry.py

backend/app/schemas/
    agent.py
    execution.py
```

We will compare these against the existing structure before creating them, so we do not duplicate existing services unnecessarily.

### **2.4 Completion criteria**

- Simple questions can be answered directly.
- Research requests are routed to the research agent.
- Intelligence requests are routed to the intelligence agent.
- Multi-step tasks can execute more than one tool.
- The user can see the steps FRIDAY followed.
- Tool failures are recorded and handled.
- The existing chat interface continues to work.

**Approval checkpoint:** We approve the orchestration design and test its request-routing behaviour before building specialised agents.

## **Phase 3 — Model manager and Ollama integration**

Estimated 1–2 days

**Objective:** Make FRIDAY independent of one hardcoded model.

We should create a common interface so the rest of the system does not need to know whether a model is running through Ollama or another provider.

### **Tasks**

1. Create a model-provider base interface.
2. Implement an Ollama provider.
3. Support configurable model names.
4. Read available models from Ollama.
5. Check whether the requested model is installed.
6. Handle model loading and connection errors.
7. Allow different models to be selected for different tasks.
8. Record the model used for each execution.
9. Measure response time.
10. Add a simple model configuration screen or settings panel.

### **Proposed model strategy**

We should benchmark the models you actually have rather than assume that the largest model is the best.

| Task                  | Model selection strategy                                    |
| --------------------- | ----------------------------------------------------------- |
| Simple conversation   | Small, responsive model                                     |
| Intent classification | Fast model                                                  |
| Research synthesis    | Best-quality model that fits available resources            |
| Coding                | Model selected after testing                                |
| Embeddings            | Separate embedding model, if semantic memory is implemented |

The current machine information suggests an RTX 4060 8GB GPU and 24GB RAM, but we will verify this during Phase 0. A larger model may run partly on CPU and may be too slow for an interactive assistant.

### **Completion criteria**

- FRIDAY can connect to Ollama through a provider interface.
- Model selection is configurable.
- Missing models produce clear errors.
- Execution records show which model was used.
- At least two available models are benchmarked if the hardware permits.

**Approval checkpoint:** Approve the model selection and benchmark results.

## **Phase 4 — Research agent and evidence verification**



Core demonstration feature

Estimated 2–3 days



**Objective:** Give FRIDAY the ability to research a subject using multiple sources and produce evidence-supported results.

This is where FRIDAY becomes more than a chatbot.

### **Tasks**

1. Create a dedicated research agent.
2. Accept a research question and optional constraints.
3. Generate a research plan.
4. Search multiple sources.
5. Retrieve relevant articles and source metadata.
6. Extract:
   - Headline.
   - Publisher.
   - URL.
   - Publication time.
   - Relevant content.
7. Remove duplicate results.
8. Compare information from different sources.
9. Identify contradictions.
10. Distinguish confirmed facts, claims, and speculation.
11. Produce a final report with citations.
12. Include a list of sources used.
13. Display limitations when information cannot be verified.

### **Proposed research lifecycle**

\#chatgpt-mermaid-\_r_7ie\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_7ie\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_7ie\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_7ie\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_7ie\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_7ie\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_7ie\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_7ie\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_7ie\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_7ie\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7ie\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7ie\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_7ie\_ p{margin:0;}#chatgpt-mermaid-\_r_7ie\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_7ie\_ .label text,#chatgpt-mermaid-\_r_7ie\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ .node rect,#chatgpt-mermaid-\_r_7ie\_ .node circle,#chatgpt-mermaid-\_r_7ie\_ .node ellipse,#chatgpt-mermaid-\_r_7ie\_ .node polygon,#chatgpt-mermaid-\_r_7ie\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .rough-node .label text,#chatgpt-mermaid-\_r_7ie\_ .node .label text,#chatgpt-mermaid-\_r_7ie\_ .image-shape .label,#chatgpt-mermaid-\_r_7ie\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_7ie\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .rough-node .label,#chatgpt-mermaid-\_r_7ie\_ .node .label,#chatgpt-mermaid-\_r_7ie\_ .image-shape .label,#chatgpt-mermaid-\_r_7ie\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_7ie\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_7ie\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7ie\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7ie\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_7ie\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_7ie\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_7ie\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_7ie\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_7ie\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_7ie\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_7ie\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_7ie\_ .icon-shape,#chatgpt-mermaid-\_r_7ie\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_7ie\_ .icon-shape p,#chatgpt-mermaid-\_r_7ie\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_7ie\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_7ie\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_7ie\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_7ie\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_7ie\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_7ie\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_7ie\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_7ie\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_7ie\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7ie\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_7ie\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7ie\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_7ie\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_7ie\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_7ie\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_7ie\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .node rect,#chatgpt-mermaid-\_r_7ie\_ .node circle,#chatgpt-mermaid-\_r_7ie\_ .node ellipse,#chatgpt-mermaid-\_r_7ie\_ .node polygon,#chatgpt-mermaid-\_r_7ie\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_7ie\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_7ie\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_7ie\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_7ie\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_7ie\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Research QuestionCreate Research PlanSearch SourcesCollect EvidenceRemove DuplicatesCompare EvidenceConflicting or MissingEvidence?Perform Additional SearchGenerate ReportAttach CitationsSave Execution TraceYesNo

### **Important reliability rules**

- A search snippet is not equivalent to a verified article.
- An old article must not be presented as breaking news.
- A source's claim must not automatically become a confirmed fact.
- If sources disagree, FRIDAY should say so.
- If information is missing, FRIDAY should say so.
- Simulated fallback results must never be presented as live evidence.

### **Suggested files**

```
backend/app/agents/
    base_agent.py
    research_agent.py

backend/app/tools/
    web_search_tool.py
    news_search_tool.py

backend/app/services/
    evidence_service.py
    citation_service.py
```

### **Completion criteria**

- FRIDAY can perform a multi-source research task.
- The report contains clickable source links.
- The report distinguishes claims from verified facts.
- Duplicate sources are handled.
- Research failures are visible rather than hidden.
- The complete workflow is covered by automated tests.

**Approval checkpoint:** We review a real research task and its generated report.

## **Phase 5 — World Intelligence agent**



Preserve FRIDAY's identity

Estimated 1–2 days



**Objective:** Upgrade the existing World Monitor feature into a specialised agent.

### **Tasks**

1. Audit the existing World Monitor service.
2. Retain its useful API integrations.
3. Standardise the risk-score output.
4. Standardise event and news output.
5. Add timestamps and source information.
6. Add data freshness indicators.
7. Handle missing country data.
8. Handle API outages.
9. Combine World Monitor data with research-agent findings.
10. Generate structured intelligence briefings.
11. Show the data sources behind each briefing.
12. Add a clear distinction between risk indicators and predictions.

### **Proposed output**

```
INTELLIGENCE BRIEFING

Region: [Selected region]
Generated: [Timestamp]

1. Risk Overview
2. Current Indicators
3. Recent Events
4. Important News
5. Source Comparison
6. Potential Implications
7. Unverified Information
8. Sources
```

The implications section should be labelled as analysis, not presented as an official World Monitor assessment or a certain prediction.

### **Completion criteria**

- Existing risk dashboard still works.
- FRIDAY can answer region-specific intelligence questions.
- Live and fallback information are distinguishable.
- The briefing includes sources and timestamps.
- The research and intelligence agents can work together.

**Approval checkpoint:** Review a complete intelligence briefing.

## **Phase 6 — Persistent memory and conversation context**

Estimated 1–2 days

**Objective:** Make FRIDAY retain useful information between sessions, with user control.

We should start with SQLite. We do not need a complex database server for the first version.

### **Memory types**

| Memory type         | Example                             |
| ------------------- | ----------------------------------- |
| Conversation memory | Previous messages in a conversation |
| User preferences    | Preferred response style            |
| Project memory      | User's ongoing project context      |
| Task memory         | Previously completed task           |
| Research memory     | Saved research summaries            |

### **Tasks**

1. Create a SQLite database.
2. Store conversation sessions.
3. Store conversation messages.
4. Create a persistent-memory data model.
5. Add explicit memory creation and retrieval.
6. Retrieve relevant context for new requests.
7. Prevent duplicate or irrelevant memories.
8. Provide a memory-management interface.
9. Allow the user to inspect and delete stored memories.
10. Add tests for memory retrieval and isolation.

### **Optional semantic retrieval**

After basic memory works, we can add embeddings and vector search.

This should be an optional extension, not a prerequisite for the first working version.

### **Completion criteria**

- Conversations persist after restarting FRIDAY.
- Relevant saved information can be retrieved.
- Memory is not mixed between different users or sessions.
- The user can inspect and delete memories.
- Sensitive information is not silently stored.

**Approval checkpoint:** Test memory across multiple sessions and approve the storage behaviour.

## **Phase 7 — Execution history, telemetry and evaluation**



Important for the architecture demonstration

Estimated 1–2 days



**Objective:** Make FRIDAY explainable and measurable.

A good AI system should not simply return an answer. We should be able to inspect how it arrived at that answer.

### **Tasks**

1. Create an execution trace for each request.
2. Record the detected intent.
3. Record the selected agent.
4. Record the generated plan.
5. Record each tool call.
6. Record tool inputs and outputs, excluding secrets.
7. Record errors.
8. Measure total execution time.
9. Measure individual tool response times.
10. Record the model used.
11. Record token usage when the provider exposes it.
12. Record user feedback.
13. Build a dashboard for execution history.
14. Create a small repeatable evaluation dataset.

### **Example execution trace**

```
REQUEST: Prepare an intelligence briefing

Intent: world_intelligence
Agent: intelligence_agent

Steps:
  1. World Monitor risk retrieval     SUCCESS
  2. Recent events retrieval          SUCCESS
  3. News search                      SUCCESS
  4. Evidence comparison              SUCCESS
  5. Report generation                SUCCESS

Total execution time: 18.4 seconds
Model: [Actual model name]
Sources collected: 8
Sources used: 5
Warnings: 1
```

These are example values, not existing measurements.

### **Evaluation tests**

We will prepare approximately 10–15 test cases initially, including:

- Simple general questions.
- World Monitor questions.
- Multi-source research.
- Missing source data.
- Conflicting information.
- API unavailable.
- Model unavailable.
- Follow-up questions requiring context.
- Incorrect or ambiguous user requests.

Measure:

- Routing accuracy.
- Tool execution success.
- Source coverage.
- Citation correctness.
- Evidence-grounding quality.
- Response time.
- Task completion rate.

### **Completion criteria**

- Every complex request has an inspectable execution trace.
- Failures are recorded.
- Performance metrics are measurable.
- We can run the same evaluation cases after future changes.
- The dashboard displays real metrics, not random values.

**Approval checkpoint:** Review execution traces and evaluation results.

## **Phase 8 — Frontend upgrade**

Estimated 2–3 days

**Objective:** Make the frontend demonstrate the architecture rather than just look like a chatbot.

We will retain useful existing React components and improve them.

### **Proposed interface**

**FRIDAY**

Local AI

**Assistant**

Chat and tasks

**Intelligence**

World Monitor and briefings

**Memory**

Saved context

**Activity**

Execution traces

**Example task execution**

1. Request received
2. Research plan created
3. World Monitor queried
4. News sources compared
5. Briefing generated

Conceptual interface preview, not a screenshot of the current application.

### **Interface sections**

1. Main assistant chat.
2. Agent activity panel.
3. Tool execution panel.
4. World intelligence dashboard.
5. Research reports and sources.
6. Memory manager.
7. Execution history.
8. Model settings.
9. System status and real hardware telemetry.

### **Completion criteria**

- The user can understand what FRIDAY is doing.
- Research sources are visible.
- Agent and tool activity is visible.
- Dashboard values are real or explicitly labelled as unavailable.
- Existing useful interface functionality remains intact.
- Layout works on common desktop resolutions.

**Approval checkpoint:** Approve the final application interface.

## **Phase 9 — Voice assistant improvements**



Optional after core features

Estimated 1–3 days



**Objective:** Improve the existing text-to-speech feature into a usable voice interface.

### **Tasks**

1. Verify existing TTS functionality.
2. Add speech-to-text input.
3. Add microphone permission handling.
4. Add speech transcription status.
5. Add interruption and cancellation where supported.
6. Add voice response playback.
7. Allow users to disable voice.
8. Consider a wake-word system only if time and performance permit.

**Important:** Voice is not the first priority. The current source inspection found text-to-speech code, but did not establish a working microphone or wake-word flow. We should test and build those separately.

### **Completion criteria**

- The user can speak a request.
- FRIDAY can transcribe it.
- FRIDAY can respond through voice.
- Text interaction still works when voice is disabled.

**Approval checkpoint:** Approve voice functionality separately.

## **Phase 10 — Scheduled monitoring and proactive briefings**



Optional extension

Estimated 1–2 days



**Objective:** Allow FRIDAY to perform user-authorised recurring tasks.

### **Example tasks**

- Generate a daily intelligence briefing.
- Check selected regions for new events.
- Monitor selected topics.
- Prepare a morning news summary.

### **Tasks**

1. Create a scheduler service.
2. Store scheduled tasks.
3. Allow the user to create and pause tasks.
4. Execute tasks at configured intervals.
5. Record execution history.
6. Notify the user of completed tasks.
7. Handle failed and missed executions.
8. Require user approval before external actions with consequences.

**Completion criteria:** Scheduled tasks execute predictably, can be paused, and have a visible history.

## **Phase 11 — Testing, security, documentation and release**



Mandatory release phase

Estimated 2 days



**Objective:** Prepare a project that can be cloned, installed, tested, demonstrated and evaluated.

### **Tasks**

1. Run the full backend test suite.
2. Run frontend checks and build.
3. Test the complete research workflow.
4. Test the intelligence workflow.
5. Test memory persistence.
6. Test Ollama unavailable scenarios.
7. Test external API failure scenarios.
8. Check secrets and environment variables.
9. Review CORS and input validation.
10. Review logging for accidentally exposed secrets.
11. Document architecture.
12. Document installation.
13. Document how to configure Ollama.
14. Document API endpoints.
15. Add screenshots.
16. Add example task traces.
17. Update GitHub README.
18. Create a tagged release or clearly identified final branch.

### **Deliverables**

- Working source code.
- Complete README.
- Architecture diagram.
- Installation instructions.
- Configuration example.
- Automated tests.
- Example research report.
- Example intelligence briefing.
- Example execution trace.
- Known limitations and future roadmap.

**Approval checkpoint:** Final release candidate approval.

## **Phase 12 — Napster application demonstration**



Final deliverable

Estimated 1 day



**Objective:** Present FRIDAY as an engineering project that you personally understand and can defend.

### **Recommended recorded demo structure**

| Segment               | Approx. time | What to demonstrate                  |
| --------------------- | ------------ | ------------------------------------ |
| Introduction          | 45 sec       | Problem and motivation               |
| Architecture          | 1 min        | How FRIDAY is structured             |
| Model integration     | 45 sec       | Local Ollama and model choice        |
| Main task             | 2 min        | Intelligence briefing                |
| Agent workflow        | 1 min        | Planning, tools and execution        |
| Evidence              | 1 min        | Sources, timestamps and uncertainty  |
| Memory and evaluation | 1 min        | Persistence and traces               |
| Conclusion            | 45 sec       | Engineering choices and future scope |

The final video should be a genuine live demonstration, not just a slideshow or prerecorded animation.

### **What you should be ready to explain**

- Why you chose local models.
- Why you created an orchestrator.
- How an agent is different from a normal chatbot.
- How tool selection works.
- How you handle API failures.
- How you evaluate output quality.
- How you handle contradictory information.
- What limitations remain.
- Which parts were developed with AI assistance and how you validated them.

# **4. What we should borrow from OpenJarvis**

Reference: [OpenJarvis GitHub repository](https://github.com/open-jarvis/OpenJarvis?utm_source=chatgpt.com).

I recommend borrowing ideas, not importing its entire codebase.

| OpenJarvis concept         | FRIDAY 2.0 decision   |
| -------------------------- | --------------------- |
| Model management           | Implement             |
| Agent orchestration        | Implement selectively |
| Tool execution             | Implement             |
| ReAct-style workflows      | Implement             |
| Research workflows         | Implement             |
| Persistent memory          | Implement             |
| Evaluation and telemetry   | Implement             |
| MCP/tool ecosystem         | Consider later        |
| Continuous monitoring      | Later phase           |
| Full framework replacement | Do not do this        |

Before reusing any OpenJarvis code, we will inspect its current licence, dependencies and implementation. We will preserve required copyright and attribution notices.

# **5. Recommended development order**

The phases above are the complete roadmap. However, considering your application deadline, I recommend this practical priority order:

## **Core build — must complete**

1. Phase 0 — Audit and baseline.
2. Phase 1 — Stabilise FRIDAY 1.0.
3. Phase 2 — Core orchestrator.
4. Phase 3 — Model manager.
5. Phase 4 — Research agent.
6. Phase 5 — World Intelligence agent.
7. Phase 7 — Execution traces and evaluation.
8. Phase 8 — Frontend upgrade.
9. Phase 11 — Testing and documentation.
10. Phase 12 — Recorded demonstration.

## **Secondary build — if time permits**

- Phase 6 — Persistent memory.
- Phase 9 — Voice improvements.
- Phase 10 — Scheduled monitoring.

I would not sacrifice testing or the recorded demonstration to squeeze in wake-word detection, many extra agents, or complicated automation.

## **6. Proposed final repository structure**

This is the intended direction. We will preserve existing files where possible and make changes incrementally.

```
FRIDAY_AI_Assistant/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── research.py
│   │   │   ├── intelligence.py
│   │   │   ├── memory.py
│   │   │   └── activity.py
│   │   │
│   │   ├── core/
│   │   │   ├── orchestrator.py
│   │   │   ├── planner.py
│   │   │   ├── execution_engine.py
│   │   │   ├── intent_classifier.py
│   │   │   └── context_manager.py
│   │   │
│   │   ├── agents/
│   │   │   ├── base_agent.py
│   │   │   ├── general_agent.py
│   │   │   ├── research_agent.py
│   │   │   ├── intelligence_agent.py
│   │   │   └── coding_agent.py
│   │   │
│   │   ├── models/
│   │   │   ├── base_provider.py
│   │   │   ├── ollama_provider.py
│   │   │   └── model_manager.py
│   │   │
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── worldmonitor_tool.py
│   │   │   ├── news_tool.py
│   │   │   ├── search_tool.py
│   │   │   └── weather_tool.py
│   │   │
│   │   ├── memory/
│   │   │   ├── database.py
│   │   │   ├── conversation_memory.py
│   │   │   └── persistent_memory.py
│   │   │
│   │   ├── evaluation/
│   │   │   ├── tracing.py
│   │   │   ├── metrics.py
│   │   │   └── evaluator.py
│   │   │
│   │   └── services/
│   │       ├── voice_service.py
│   │       └── evidence_service.py
│   │
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── hooks/
│
├── data/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── DEMO_GUIDE.md
│
├── scripts/
├── .env.example
├── README.md
└── requirements.txt
```

This is a target structure, not a requirement to create every folder immediately. We will only create a module when its phase needs it.

# **7. Our development and approval process**

I suggest we use this exact workflow for every phase:

1. **Design**

   I explain the technical design, the reason for the change, and how it fits the existing project.
2. **Approve**

   You approve the design before we make changes.
3. **Implement**

   I provide complete files or precise modifications, not disconnected code fragments.
4. **Run**

   You receive exact PowerShell commands and VS Code instructions.
5. **Test**

   We verify the feature with expected outputs and failure cases.
6. **Review and checkpoint**

   We review the code, update documentation and create a Git checkpoint before continuing.

### **Rules I recommend following**

1. Never delete a working FRIDAY 1.0 feature just to replace it with a newer implementation.
2. Never make several architectural changes at once without testing them.
3. Never expose API keys, passwords or private configuration in GitHub.
4. Never claim a feature works until we have tested it.
5. Keep local Ollama as the primary model path.
6. Make the AI workflow observable, so you can explain what FRIDAY did.
7. Keep a working Git checkpoint after each completed phase.
8. You should understand every important component well enough to explain it in your interview.
