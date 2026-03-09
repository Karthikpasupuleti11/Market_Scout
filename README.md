# Market Intelligence Scout

**Industry-grade multi-agent system** for automated market intelligence gathering. Built with LangGraph, NVIDIA NIM, and self-contained agent packages.

## Architecture

```
User Request
     │
     ▼
┌─────────────┐
│  Input      │  ← Validates company names, blocks prompt injection
│  Guardrail  │
└─────┬───────┘
      ▼
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Supervisor │────▶│  Research Agent   │────▶│  Analysis Agent  │
│  (Router)   │◀────│  • Planner       │     │  • Planner       │
│             │     │  • Search ‖      │     │  • Filter ‖      │
│  LLM-driven │     │  • Scraper ‖     │     │  • Extractor ‖   │
│  dynamic    │     │  • Date filter   │     │  • Verifier      │
│  routing    │     │  • Self-critic   │     │  • Scorer        │
│             │     │  • Memory        │     │  • Self-critic   │
└──────┬──────┘     └──────────────────┘     │  • Memory        │
       │                                      └──────────────────┘
       ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Critic Agent │    │ Synthesis Agent  │───▶│ Output Guardrail │
│ • Approve    │    │ • Report gen     │    │ • Prompt leak    │
│ • Revise     │    │ • Memory         │    │ • Data exposure  │
│ • Memory     │    └──────────────────┘    │ • Score sanity   │
└──────────────┘                            │ • URL validation │
                                            └────────┬─────────┘
  ‖ = Parallel execution (ThreadPoolExecutor)         ▼
                                                   User
```

## Project Structure

```
Market_Scout/
├── agents/                          # Self-contained agent packages
│   ├── supervisor/                  # Dynamic routing agent
│   │   ├── agent.py                 #   LLM-driven routing logic
│   │   ├── planner.py               #   Deterministic routing rules
│   │   └── memory.py                #   Routing history tracker
│   │
│   ├── research_agent/              # Web research agent
│   │   ├── agent.py                 #   Main ReAct loop
│   │   ├── planner.py               #   Search query generation
│   │   ├── critic.py                #   Self-review (coverage, diversity)
│   │   ├── memory.py                #   Query/URL tracker
│   │   └── tools/                   #   Agent-specific tools
│   │       ├── search.py            #     Tavily search (PARALLEL, 4 threads)
│   │       ├── scraper.py           #     Web scraping (PARALLEL, 8 threads)
│   │       └── date_filter.py       #     7-day recency filter
│   │
│   ├── analysis_agent/              # Data analysis agent
│   │   ├── agent.py                 #   Full analysis pipeline
│   │   ├── planner.py               #   Strategy planning
│   │   ├── critic.py                #   Self-review (quality, evidence)
│   │   ├── memory.py                #   Extraction history
│   │   └── tools/                   #   Agent-specific tools
│   │       ├── content_filter.py    #     Relevance filter (PARALLEL, 5 threads)
│   │       ├── authority.py         #     Source credibility check
│   │       ├── extractor.py         #     Feature extraction (PARALLEL, 5 threads)
│   │       ├── verifier.py          #     SBERT cross-source clustering
│   │       └── scorer.py            #     Confidence scoring formula
│   │
│   ├── critic_agent/                # Quality review agent
│   │   ├── agent.py                 #   Approve/Revise decisions
│   │   └── memory.py                #   Review history
│   │
│   ├── synthesis_agent/             # Report generation agent
│   │   ├── agent.py                 #   Executive report generator
│   │   └── memory.py                #   Report tracking
│   │
│   └── output_guardrail/            # Output security gate
│       └── agent.py                 #   5 validation checks
│
├── graph/                           # LangGraph orchestration
│   ├── builder.py                   #   Pipeline assembly + conditional edges
│   └── state.py                     #   Shared GraphState schema
│
├── nodes/                           # Standalone pipeline nodes
│   └── guardrails.py                #   Input validation + prompt injection guard
│
├── app/                             # FastAPI application
│   ├── main.py                      #   Server + API endpoints
│   └── config.py                    #   Settings (env-driven)
│
├── llm/                             # LLM client
│   └── nvidia_client.py             #   NVIDIA NIM (LLaMA 3.3 70B)
│
├── cache/                           # Caching layer
│   └── redis_client.py              #   Redis operations
│
├── database/                        # PostgreSQL persistence
│   └── models.py                    #   SQLAlchemy models
│
├── observability/                   # Monitoring
│   ├── metrics.py                   #   Prometheus counters/histograms
│   └── tracing.py                   #   OpenTelemetry setup
│
├── frontend/                        # React dashboard
├── docker-compose.yaml              #   PostgreSQL, Redis, Prometheus, Grafana
├── requirements.txt
└── README.md
```

## Observability & Monitoring

The system includes a fully configured **Prometheus + Grafana** stack to monitor pipeline health in real-time.

- **Pipeline Metrics**: Tracks active runs, pass/fail rates, and guardrail blocks.
- **Node Latency**: Measures p95 latency for every agent and tool execution.
- **LLM Cost & Usage**: Tracks token usage by agent (prompt vs completion) and LLM API call success rates.
- **Intelligence Metrics**: Tracks features extracted, confidence score distribution, and URLs discarded/scraped.

Access the dashboard at `http://localhost:3000` (default Grafana).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | LangGraph (StateGraph, conditional edges) |
| **LLM** | NVIDIA NIM — LLaMA 3.3 70B Instruct |
| **Search** | Tavily API |
| **Embeddings** | Sentence-BERT (all-MiniLM-L6-v2) via HuggingFace |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | React |
| **Database** | PostgreSQL (SQLAlchemy) |
| **Cache** | Redis |
| **Monitoring** | Prometheus + Grafana |
| **Tracing** | OpenTelemetry |

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Karthikpasupuleti11/Market_Scout.git
cd Market_Scout
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Set environment variables (.env)
NVIDIA_API_KEY=nvapi-...
TAVILY_API_KEY=tvly-...
HF_API_TOKEN=hf_...

# 3. Start infrastructure
docker compose up -d  # PostgreSQL, Redis, Prometheus, Grafana

# 4. Run the server
uvicorn app.main:app --reload

# 5. Submit a query
curl -X POST http://localhost:8000/run-agent \
  -H "Content-Type: application/json" \
  -d '{"company_name": "OpenAI"}'
```

## Multi-Agent Patterns Used

| Pattern | Implementation |
|---------|---------------|
| **Orchestrator + Workers** | Supervisor dynamically routes to specialist agents |
| **Tool-Use Agents** | Research + Analysis agents use ReAct-style tool calling |
| **Critic/Review Loop** | Critic Agent can reject and trigger re-analysis (max 3 iterations) |
| **Self-Contained Agents** | Each agent has own planner, critic, memory, tools |
| **Parallel Execution** | ThreadPoolExecutor for I/O-bound operations (4-8 threads) |
| **Dual-Layer Guardrails** | Input guardrail (6 security checks) + Output guardrail (5 validation checks) |

## License

MIT
