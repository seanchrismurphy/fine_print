# Insurance PDS Q&A

A retrieval-augmented generation system for querying and comparing Australian home insurance Product Disclosure Statements.

**Live demo:** [link when deployed]

---

## The problem

Australian home insurance consumers face a genuine information asymmetry problem at purchase time. Insurers publish Product Disclosure Statements that run to 60-80 pages of legal language, and the terminology is not consistent across providers. "Flood", "storm water", "rainwater", and "surface water" are legally distinct terms that determine whether a claim is paid or rejected — and different insurers define them differently. Reading four PDSs side by side to make a coverage decision is not a realistic expectation of a consumer.

This system makes those documents interrogable in plain language and comparable across insurers.

---

## What it does

- Answers coverage questions grounded in specific policy language, with source citations to the relevant document and page
- Compares how multiple insurers define a term or handle a scenario
- Routes queries intelligently — comparison questions decompose into per-insurer sub-questions, retrieved independently and synthesised together
- Surfaces the retrieval chain and reasoning trace via LangSmith

**Corpus:** Home insurance PDS documents from NRMA, Allianz, AAMI, and Suncorp.

---

## Architecture

*Diagram to be added.*

The system uses a LangGraph flow with four nodes:

**Query Classifier** — determines whether a query is single-document factual, cross-insurer comparison, or out-of-scope. Out-of-scope queries are handled directly without retrieval.

**Query Decomposer** — for comparison queries, breaks the question into sub-questions targeting each insurer's document independently.

**Parallel Retriever** — executes hybrid retrieval (BM25 + dense, combined with Reciprocal Rank Fusion) for each sub-question concurrently.

**Synthesiser** — generates the final answer from retrieved contexts, with inline citations to source documents.

---

## Key decisions

*To be written as the project progresses. See `docs/decisions/` for working notes.*

Topics to cover:
- Chunking strategy and why (chunk size, overlap, handling of defined terms sections)
- Hybrid retrieval justification for the insurance domain
- LangGraph flow design and why sequential sub-question retrieval improves comparison queries
- Evaluation-driven iteration: what changed and what the delta was

---

## Evaluation

*To be completed after Phase 4.*

RAGAS metrics across 25-30 manually constructed ground truth Q&A pairs, covering single-document factual, exclusion surfacing, and cross-insurer comparison query types.

| Metric | Baseline | After iteration |
|---|---|---|
| Faithfulness | — | — |
| Answer relevancy | — | — |
| Context precision | — | — |
| Context recall | — | — |

---

## Known limitations and next steps

*To be completed.*

Planned stretch goals not in scope for v1:
- **Exclusion checker:** proactively surface relevant exclusions the user did not ask about, as a separate LangGraph node
- **Pinecone:** replace local Chroma with managed vector storage for namespace-per-insurer support

---

## Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph + LangChain |
| Embeddings | OpenAI text-embedding-3-small |
| Vector store | Chroma |
| Retrieval | Hybrid BM25 + dense (RRF) |
| LLM | GPT-4o-mini |
| Backend | FastAPI |
| Frontend | Streamlit |
| Observability | LangSmith |
| Evaluation | RAGAS |
| Deployment | Azure Container Apps |

---

## Setup

*To be completed.*

```bash
# Clone the repo
git clone [repo url]
cd [repo name]

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Run locally
# Instructions to follow
```

**Required environment variables:**

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_TRACING_V2` | Set to `true` |
| `LANGCHAIN_PROJECT` | Your LangSmith project name |

---

## Docs

Working notes live in `docs/`:

- `docs/decisions/` — one file per architectural decision, written as decisions are made
- `docs/setup/` — environment setup and infrastructure notes
- `docs/evaluation/` — RAGAS outputs, failure case analysis
- `docs/progress.md` — running project log
