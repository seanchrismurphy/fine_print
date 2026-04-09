# Insurance PDS Q&A System — Project Brief (v3)

---

## Problem Statement

Australian insurance consumers face a specific, consequential information asymmetry problem. At purchase time, they are handed multiple 60–80 page Product Disclosure Statements written in legal language, with inconsistent terminology across insurers for equivalent concepts. This is not an abstract problem.

In Australian home insurance, "flood," "storm water," "rainwater," and "surface water" are legally distinct terms that determine whether a claim is paid or rejected. Different insurers define them differently. A homeowner asking whether they are covered for damage after heavy rain may receive opposite answers from different insurers, for reasons buried in definitions sections they have never read. This system makes those documents interrogable and comparable, so a consumer can ask a plain-language question and get an answer grounded in the actual policy language — with source citations so they can verify it themselves.

The canonical query this system is designed to answer: **"If my house floods during a storm, will I be covered?"** This query is deliberately ambiguous in the way real consumer questions are ambiguous. It crosses the flood/storm boundary intentionally. A well-functioning system should retrieve the relevant definitions from all four insurers, surface the terminological differences, and produce an answer that is both accurate and useful — telling the consumer which insurers are likely to pay and which are likely to dispute, with the relevant policy language quoted verbatim. This query will be used throughout development as the primary test of whether the system is working.

---

## Phase 1 — Corpus Construction (Weeks 1–2)

**Goal:** A structured, version-controlled document corpus with enough ground truth coverage to drive meaningful evaluation.

### Documents

Select NRMA, Allianz, AAMI, and Suncorp. All publish home insurance PDS documents publicly. All have meaningful differences in how they define flood, storm damage, and related exclusions. Download PDFs directly from insurer websites — do not scrape dynamically. Version-control the raw PDFs and record the retrieval date for each.

### Metadata Registry

Build a document metadata registry. For each document, record: insurer name, product line, document version, date retrieved, and source URL. This becomes the foundation for source citations in the frontend and for audit purposes.

### Structural Audit

Before writing a single line of retrieval code, read all four documents and produce a written audit of their structural heterogeneity. Key questions: Does each document have a consolidated defined terms section, or are definitions scattered? Are exclusions in one place or distributed across coverage sections? How are coverage limits presented — as tables, inline text, or schedules? Are definitions cross-referenced within the document?

This audit is not administrative work. It directly determines the chunking strategy in Phase 2. The structural differences across these four documents are what make chunking decisions non-trivial, and documenting them is what makes the chunking section of the README defensible. Keep notes as you go.

### Ground Truth Dataset

Construct 35–40 ground truth Q&A pairs manually. This is the most important deliverable of Phase 1, and it is worth investing more time here than feels comfortable. Weak ground truth produces misleading evaluation results downstream.

Distribute pairs across three types:

**Single-document factual (10–12 pairs):** Direct definition or coverage questions targeting one insurer. Example: "What is the flood definition under Allianz home insurance?" Each pair must include the source document, page number, and verbatim relevant text.

**Exclusion surfacing (8–10 pairs):** Questions about what is explicitly excluded. Example: "What events are excluded from storm damage cover under NRMA?" These are harder to construct well because exclusion language is often scattered across sections — which is exactly why they are worth including.

**Cross-insurer comparison (15–18 pairs):** Questions requiring synthesis across multiple documents. Example: "Which of the four insurers provides the broadest definition of storm damage?" This is the query type where the agentic layer will matter most, and having sufficient comparison pairs in the ground truth is what makes the Phase 4 evaluation credible. Do not underinvest here.

Label each pair with: query type, source documents and page numbers, and the key text the answer must reference. For comparison queries, note which insurers hold the most relevant definitions and what the expected answer structure looks like.

At the end of Phase 1, you should have: four versioned PDFs, a metadata registry, a written structural audit, and 35–40 annotated ground truth pairs. These are the inputs to everything that follows.

---

## Phase 2 — Core Retrieval Pipeline (Weeks 2–5)

**Goal:** A working retrieval pipeline with domain-justified design decisions and measured evidence for the choices made.

### PDF Parsing

Implement PDF parsing with pdfplumber or pymupdf. These handle insurance PDFs more reliably than LangChain's default loaders and give explicit control over page metadata. Attach document metadata — insurer name, document version, page number — to every chunk at parse time. This metadata will flow through to source citations in the API response.

### Structure-Aware Chunking

Do not start with a generic recursive character splitter. The structural audit from Phase 1 tells you what the documents actually look like — use that knowledge.

The primary failure mode of naive chunking in PDS documents is splitting definitions mid-clause. A flood definition may run 200–400 words with sub-clauses and cross-references. A recursive splitter at 512 tokens will likely bisect it, producing two chunks that each contain incomplete information. When retrieved separately, neither chunk fully answers a definition query.

Implement a structure-aware chunker that uses document headings and section markers to identify defined terms and keep each definition as an atomic unit. For the exclusions sections, keep sub-clauses together. For coverage limit tables, treat each row as a unit.

Implement the naive recursive splitter first as a baseline. Run it against your ground truth pairs and note where it fails. Then implement the structure-aware approach and measure the delta. Documenting what you tried and why you changed it is a more valuable README contribution than simply documenting what you ended up with.

### Embeddings and Vector Store

Generate embeddings with OpenAI text-embedding-3-small and store in Chroma with persistence to disk. Local Chroma is sufficient for development. Persistence to Azure Blob Storage in deployment is discussed in Phase 6 — note in the architecture that this approach has latency implications at container startup and is appropriate for a single-replica deployment at this corpus size.

### Hybrid Retrieval

Implement hybrid retrieval combining BM25 and dense embeddings with Reciprocal Rank Fusion. The domain justification is explicit and should appear in the README: pure semantic retrieval fails on defined-term queries because "flood" and "rainwater" are semantically close in a general-purpose embedding model, which has no reason to treat them as legally distinct. BM25 catches exact term matches regardless of semantic proximity, which is what you need when a defined term is the crux of the query. Use rank_bm25 for the keyword side and combine ranked lists with RRF.

In the frontend, do not surface a generic "similarity score" per chunk. RRF does not produce one — it produces a fused rank from two independent ranked lists. Surface the BM25 rank and dense rank separately, or surface the RRF rank and label it as such. This is a minor frontend detail that will come up if anyone looks closely at the UI, and having a correct answer ready is better than having an incorrect label.

### Ablation Study

Before moving to Phase 3, run your ground truth set against three retrieval configurations: dense-only, BM25-only, and hybrid RRF. Record faithfulness and answer relevancy for each configuration across all three query types.

The goal of this ablation is not to prove that hybrid is always best. The goal is to identify which query types benefit from which retrieval approach and to have evidence for the hybrid choice. You will almost certainly find that BM25-only outperforms dense-only on definition queries, and that dense-only performs better on paraphrased questions that do not match defined term keywords. The hybrid approach should perform better overall, but the interesting result is the breakdown by query type. This breakdown belongs in the README as a table.

### Baseline Evaluation

Before building the LangGraph layer, run RAGAS on your Phase 2 pipeline against all ground truth pairs. Record: faithfulness, answer relevancy, context precision, context recall. For comparison queries, note that the Phase 2 pipeline is not designed to answer them — it will retrieve from a single document or at best inconsistently across documents. Record these scores as the Phase 2 baseline, but frame them correctly in the README: the comparison query scores are not a failure of retrieval quality, they are evidence that the query type requires a different system architecture.

Identify the three worst-performing ground truth pairs — one from each query type — and trace each failure to its root cause before moving on. Is it a retrieval failure? A ranking failure? A chunking failure? A synthesis failure? This analysis will drive the iteration target in Phase 4 and will become the error analysis section of the README.

Do not add the Cohere reranker at this stage. If RAGAS results specifically identify retrieval precision as the primary failure mode and the ablation study suggests reranking would help, revisit it. Otherwise skip it — a local cross-encoder from sentence-transformers is a better option than Cohere if you do add one, because it has no external dependency and is more interesting to explain.

---

## Phase 3 — Agentic Layer with LangGraph (Weeks 5–8)

**Goal:** A stateful, multi-step reasoning flow that justifies the "agentic" label, with every design decision traceable to a concrete problem it solves.

Build the LangGraph flow sequentially. Get the linear path working and tested against ground truth before adding any parallel branches. Parallel branch debugging is expensive — do not enter it with an untested linear foundation.

### Node 1 — Query Classifier

Classifies incoming queries into: single-document factual, cross-insurer comparison, or out-of-scope. Out-of-scope includes greetings, questions about insurance products not in the corpus, and questions that cannot be answered from PDS documents (e.g., "should I buy home insurance?").

The classifier is load-bearing. A misclassified comparison query either returns a partial answer drawn from one document or fails silently. Evaluate the classifier explicitly: using your ground truth pairs, measure classification accuracy separately from retrieval quality. This is one additional column in your evaluation table and approximately one hour of additional work. It is worth doing because it shows you understand where the system can fail, not just where it succeeds.

### Node 2 — Query Decomposer (comparison queries only)

Breaks a comparison question into sub-questions, one per relevant insurer. "Which insurer defines flood most broadly?" becomes four parallel sub-questions, each targeting one insurer's document namespace. This node should also identify which insurers are relevant — a query might specify two insurers explicitly, in which case decomposition targets only those two.

### Node 3 — Parallel Retriever

Executes retrieval for each sub-question independently and concurrently. This is where LangGraph's graph structure earns its place. Expect this node to take the most debugging time — state management across parallel branches and the join behaviour before synthesis require careful attention. Single-document factual queries bypass this node entirely and go directly to a single retrieval call.

### Node 4 — Synthesiser

Generates the final answer from one or more retrieved contexts. For comparison queries, the synthesiser has a harder job than for factual queries: it must compare definitions across insurers and produce a judgment, not just a summary.

Treat the synthesis prompt for comparison queries as a first-class design problem. A naive prompt will produce hedged, non-committal answers that describe each insurer's position without answering the question. The prompt should explicitly instruct the model to: quote the relevant definition from each insurer, identify the key terminological differences, and make a direct claim about which definition is broadest or most consumer-friendly — with the quoted text as the evidence. Iterate on this prompt against your comparison query ground truth pairs until the answers are direct and well-supported.

### Node 5 — Confidence Signaller

Sits between the synthesiser and the response. Its job is to assess whether the retrieved context is actually sufficient to answer the question — not whether an answer was generated, but whether the answer is grounded in the right content.

Specifically: if the query asks about flood coverage and the retrieved chunks contain storm damage definitions but not a flood definition, the system should not return an answer as if it found what it was looking for. The confidence signaller should detect this mismatch and return a response like: "I found relevant content about storm damage but could not locate a specific flood definition in this document. The relevant section may be on pages X–Y — I'd recommend checking directly."

This behaviour is evaluable: you can identify ground truth pairs where the system should trigger uncertainty (e.g., queries about defined terms that are absent from one insurer's document) and measure whether it does. It is also the most interesting architectural decision in the whole system from an interview perspective, because it demonstrates that you thought about what the system should do when retrieval is incomplete — not just when it succeeds.

### Conditional Routing Summary

- Comparison query: Classifier → Decomposer → Parallel Retriever → Synthesiser → Confidence Signaller → Response
- Single-document factual: Classifier → Retriever → Synthesiser → Confidence Signaller → Response
- Out-of-scope: Classifier → Direct Response (no retrieval)

---

## Phase 4 — Evaluation and Iteration (Weeks 6–9, overlapping with Phase 3)

**Goal:** A credible evaluation story with a before/after delta and an honest account of remaining failure modes.

### Framing the Before/After Correctly

The evaluation story has two distinct components and they should not be conflated.

For single-document factual queries, the before/after comparison is an apples-to-apples metric improvement: the same query type, measured on the same metric, before and after an intervention (chunking improvement, k tuning, or reranker). This is where a clean RAGAS delta lives.

For comparison queries, the before/after is not a metric improvement — it is a capability addition. The Phase 2 pipeline cannot meaningfully answer comparison queries; it was not designed to. The Phase 3 pipeline can. Frame this correctly in the README: "Phase 2 did not support cross-insurer comparison queries. Phase 3 introduces parallel retrieval and comparative synthesis, enabling this query class for the first time. The following RAGAS scores represent the Phase 3 baseline for comparison queries." That framing is more accurate and more impressive than implying a metric lift on a query type the Phase 2 system could never have scored well on.

### Iteration Target

Based on the Phase 2 failure analysis, pick one thing to iterate on before finalising Phase 3. The most productive candidates are: chunk size or overlap for definition queries, retrieval k, or the synthesis prompt for comparison queries. Measure the delta on your ground truth set before moving on. Document what changed and why in the README iteration section.

### Error Analysis

This is a first-class deliverable, not a footnote. After evaluation, select three failure cases — one from each query type — that the system still gets wrong after iteration. For each one, trace the failure back to its root cause and write it up as a short paragraph. Be specific: "Query X fails because the Allianz flood definition is split across pages 23 and 24, and the chunker treats the page break as a section boundary, producing two incomplete chunks that are never retrieved together. This is a structural parsing failure, not a retrieval failure." A failure analysis written at this level of specificity tells a technical reviewer more about your engineering judgment than a clean metrics dashboard.

---

## Phase 5 — Serving Layer and Observability (Weeks 8–10)

**Goal:** A clean, deployable interface that surfaces the system's reasoning at every step.

### FastAPI Backend

`/query` endpoint accepting a question and optional insurer filter.

Response payload includes:
- Answer text
- Source citations with insurer name and page number
- Retrieved chunk previews
- Query type as classified by Node 1
- BM25 rank and dense rank for each retrieved chunk (not a single "similarity score")
- LangGraph node traversal path (which nodes fired, in order)

### Streamlit Frontend

Chat interface with a sidebar for insurer filtering (all four, or select a subset for single-insurer queries). Below each answer: an expandable "Retrieved Sources" panel showing chunk previews, BM25 rank, dense rank, and document metadata. A node traversal indicator showing which LangGraph nodes fired for that query — this makes the routing behaviour visible to a non-technical user and is a good interview talking point.

The canonical demo query ("If my house floods during a storm, will I be covered?") should be the placeholder text in the chat input. Anyone who opens the app and hits enter should immediately see the system doing its most interesting work.

### LangSmith Observability

Instrument every LangGraph node. The trace for a comparison query should be readable enough to walk through in an interview: classifier decision, decomposer sub-questions, each parallel retrieval branch independently, synthesiser input/output, confidence signaller assessment.

Do not attempt to surface the LangSmith trace URL synchronously in the API response — trace sync latency makes this unreliable. Instead, capture representative traces for the canonical demo query and for representative failure cases, screenshot them, and include them in the README. Be able to pull up a live trace in an interview. That achieves the same demo goal without fragile integration work.

---

## Phase 6 — Deployment and README (Weeks 10–12)

**Goal:** A live deployment and a README that reads like an engineering post-mortem, not a feature list.

### Deployment

Azure Container Apps. Containerise FastAPI and Streamlit separately. Use environment variables for API keys injected at container startup — Azure Key Vault adds operational overhead with no visible portfolio signal at this project scale. Persist the Chroma index to Azure Blob Storage. Note in the README that this approach syncs the index directory at container startup, which introduces startup latency and is appropriate for a single-replica deployment. This is a known limitation, not an architectural weakness, and framing it correctly is more credible than leaving it undiscussed.

### README as Engineering Narrative

The README should read like a short engineering post-mortem: a problem, a series of design decisions made in response to concrete evidence, results, and an honest account of what remains. Not a feature list. Not documentation.

Each key decision should be written as a short narrative: what problem prompted the decision, what was tried first, what evidence changed the direction, and what was chosen. Write these as you make the decisions — the specific details are easy to forget after the fact and the decisions themselves are what technical reviewers will read most carefully.

The README structure below is a template. Sections marked **[FILL IN]** are to be completed during and after the build. Sections with draft text can be adapted or replaced.