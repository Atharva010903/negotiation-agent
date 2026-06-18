# Multi-Agent Procurement Negotiation Platform

A production-ready AI system that simulates real-world procurement negotiations using autonomous agents, Retrieval-Augmented Generation (RAG), and human-in-the-loop decision making.

The platform orchestrates multiple AI agents through **LangGraph**, grounds decisions with **ChromaDB-based retrieval**, enables **human intervention at critical checkpoints**, and provides a **real-time dashboard** for monitoring negotiations and analytics.

---

#  Key Features

- **Buyer Agent** that negotiates within a predefined budget while maximizing value.
- **Seller Agent** that strategically defends pricing and maximizes profit margins.
- **Mediator Agent** that evaluates negotiation progress and decides whether to continue, request human intervention, or conclude the negotiation.
- **Retrieval-Augmented Generation (RAG)** using ChromaDB and Sentence Transformers to ground negotiations in historical procurement benchmarks.
- **Human-in-the-Loop Support** using LangGraph interrupts, allowing users to modify constraints or approve deals during execution.
- **Persistent Logging** of every negotiation round using SQLite for replay, auditing, and analytics.
- **Interactive Streamlit Dashboard** for live monitoring, transcript visualization, and negotiation insights.
- **REST APIs** built with FastAPI for seamless integration and programmatic control.

---

# System Architecture

```
                         +-------------------------+
                         |   Streamlit Dashboard   |
                         |  Live Monitoring & HITL |
                         +------------+------------+
                                      |
                                      |
                                  FastAPI APIs
                                      |
                                      |
                         +------------v------------+
                         |     LangGraph Engine    |
                         |-------------------------|
                         | Setup                   |
                         | RAG Retrieval           |
                         | Buyer Agent             |
                         | Seller Agent            |
                         | Mediator Agent          |
                         | Conditional Routing     |
                         | Human Interrupt         |
                         +------------+------------+
                                      |
                   +------------------+------------------+
                   |                                     |
          +--------v--------+                 +----------v---------+
          |    ChromaDB     |                 |      SQLite        |
          | Benchmark Store |                 | Negotiation Logs   |
          +-----------------+                 +--------------------+
```

The negotiation workflow follows:

```
Setup
   │
   ▼
Retrieve Market Benchmarks (RAG)
   │
   ▼
Buyer Agent ⇄ Seller Agent
        │
        ▼
   Mediator Agent
        │
 ┌──────┼───────────────┐
 │      │               │
 ▼      ▼               ▼
Loop   Human HITL   Finish
```

---

# Tech Stack

| Component | Technology |
|-----------|------------|
| Multi-Agent Orchestration | LangGraph |
| Prompt Management & Structured Outputs | LangChain |
| Buyer & Seller Models | Groq – Qwen3-32B |
| Mediator Model | Groq – Llama-3.1-8B-Instant |
| Retrieval-Augmented Generation | ChromaDB |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Backend APIs | FastAPI |
| Dashboard | Streamlit + Plotly |
| Persistence | SQLite |
| Data Validation | Pydantic v2 |

---

# Agent Responsibilities

## Buyer Agent

- Negotiates the lowest possible procurement cost.
- Respects budget ceilings and business priorities.
- Uses retrieved benchmark data to justify offers.
- Runs on **Qwen3-32B with thinking mode enabled** for strategic reasoning.

## Seller Agent

- Maximizes revenue while protecting minimum acceptable pricing.
- Generates counter-offers backed by benchmark data.
- Runs on **Qwen3-32B with thinking mode disabled** for lower latency.

## Mediator Agent

- Does **not negotiate**.
- Evaluates convergence, concession velocity, and agreement likelihood.
- Decides whether to:
  - Continue negotiation
  - Trigger human intervention
  - Mark negotiation as successful
  - Terminate negotiation

The mediator uses **Llama-3.1-8B-Instant** for efficient decision making.

---

# Retrieval-Augmented Generation (RAG)

To ensure negotiations are grounded in realistic market information, the platform uses a lightweight RAG pipeline.

- Synthetic procurement benchmark dataset (~50 records)
- ChromaDB vector database
- Sentence Transformer embeddings (`all-MiniLM-L6-v2`)
- Top-k retrieval before every negotiation round

Benchmark records include:

- Industry
- Average discount
- Payment terms
- Delivery timelines
- Minimum order quantity (MOQ)
- Contract value
- Negotiated outcomes
- Supplier ratings

Both buyer and seller agents reference retrieved benchmarks when generating offers.

---

# Human-in-the-Loop Workflow

The mediator can pause execution using LangGraph's `interrupt()` mechanism when:

- Negotiations stagnate
- Offers significantly converge
- Maximum rounds are reached
- Manual review is recommended

During interruption, users can:

- Approve the current negotiation
- Reject the deal
- Modify buyer constraints
- Modify seller constraints
- Inject additional instructions
- Terminate the negotiation

Execution resumes seamlessly after intervention.

---

# Negotiation Persistence

Every negotiation round is stored in SQLite, including:

- Session ID
- Timestamp
- Round number
- Buyer offer
- Seller offer
- Agent rationales
- Retrieved benchmark references
- Mediator decisions
- Human interventions
- Final negotiation outcome

This enables complete replay, auditing, and post-negotiation analytics.

---

# Dashboard Features

The Streamlit dashboard provides:

- Live negotiation progress
- Buyer and seller offers
- Mediator decisions
- Price convergence visualization
- Negotiation transcript viewer
- Human override controls
- Agreement statistics
- Concession analytics
- Benchmark utilization insights

---

# REST API

| Method | Endpoint | Description |
|----------|--------------------------|--------------------------------|
| POST | `/start_negotiation` | Start a new negotiation |
| POST | `/next_round` | Continue a paused negotiation |
| POST | `/human_override` | Apply manual intervention |
| GET | `/status/{session_id}` | Retrieve current session status |
| GET | `/transcript/{session_id}` | Retrieve negotiation transcript |
| GET | `/analytics` | Platform analytics |
| GET | `/health` | Service health check |

---

# Project Structure

```text
project/
│
├── app/
│   ├── agents/
│   ├── graph/
│   ├── rag/
│   ├── prompts/
│   ├── models/
│   ├── db/
│   ├── api/
│   └── dashboard/
│
├── data/
├── chroma_db/
├── logs/
├── tests/
├── requirements.txt
└── README.md
```

---

# Getting Started

## 1. Clone the Repository

```bash
git clone <repository-url>
cd negotiation_agent
```

## 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
# or
venv\Scripts\activate         # Windows
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

```bash
cp .env.example .env
```

Add your **Groq API Key**:

```env
GROQ_API_KEY=your_api_key_here
```

## 5. Generate Benchmark Dataset

```bash
python -m app.rag.generator
```

## 6. Start the Backend

```bash
uvicorn app.api.routes:app --reload
```

## 7. Launch the Dashboard

```bash
streamlit run app/dashboard/app.py
```

## 8. Run Tests

```bash
pytest tests -v
```

---

# Learning Outcomes

This project demonstrates practical applications of:

- Multi-agent AI systems
- LangGraph stateful orchestration
- Retrieval-Augmented Generation (RAG)
- Human-in-the-loop workflows
- Structured LLM outputs
- Model specialization and routing
- FastAPI service development
- Real-time AI monitoring dashboards
- Persistent state management and analytics
