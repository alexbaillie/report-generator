# AI Improvements Notes (Developer)

This document collects practical, developer-oriented ideas to improve AI generation quality, safety, and maintainability in this repo.

It is written for the current architecture:

- Backend prompts assembled in `backend/services/llm_service.py` and `backend/services/report_generator.py`
- Inference via Ollama using `backend/services/ollama_client.py`

## Current state (baseline)

- Model: `tinyllama` (hard-coded in `llm_service.py`)
- Prompt style:
  - `llm_service.py` asks for a “complete updated report” given current content + instruction.
  - `report_generator.py` generates per-section paragraphs and asks for “only the content” and “no headers”.
- Hyperparameters:
  - `ollama_client.py` sets `temperature=0.7` by default, and controls length via `num_predict`.

The current behavior is simple and works, but it will likely produce:

- occasional hallucinations (invented test scores, invented history)
- formatting drift (sections not matching the template)
- variability in tone and clinical phrasing

## Prompt engineering improvements

### 1) Add explicit constraints (hallucination and scope control)

When generating clinical report text, a strong baseline is:

- Do not invent facts.
- If required info is missing, output placeholders or “insufficient information”.
- Keep language neutral and clinically appropriate.

Where to apply:

- `backend/services/llm_service.py` when editing an entire report.
- `backend/services/report_generator.py` when generating a section.

Example constraint ideas (not code):

- “Use only the information provided in ‘Relevant Source Documents’ and ‘Information for … section’.”
- “If a score/date/name is not provided, do not guess. Use `[INSERT ...]`.”
- “Do not add diagnoses unless explicitly provided.”

### 2) Use a structured prompt template and separators

Models respond more reliably when you structure the prompt with consistent separators.

Suggested structure:

- System role: clinical report assistant
- Task: generate section X
- Inputs:
  - Template guidance
  - Client data
  - Document excerpts
- Output format constraints

Use strong delimiters:

- `---BEGIN CONTEXT---` / `---END CONTEXT---`
- `---BEGIN DOCUMENTS---` / `---END DOCUMENTS---`

This reduces “prompt leakage” and improves adherence.

### 3) Make the output format machine-checkable

If you want predictable output:

- ask for JSON output with keys like `section_content`, `citations_used`, `missing_inputs`
- or ask for a strict Markdown block

Then validate server-side and surface a helpful error if it fails.

This is especially valuable if you later implement:

- automatic assembly of multi-section reports
- export to DOCX/PDF

### 4) Use “plan then write” for longer sections

For long narrative sections, ask the model to:

1) list bullet points it will cover (based only on inputs)
2) then produce the paragraph

This improves coherence, but it does increase token usage.

### 5) Add section-specific prompt templates

Right now, `get_default_section_guidance()` provides a general mapping.

To improve quality:

- maintain a section-specific prompt “library” (one template per section)
- include:
  - desired structure
  - typical clinical phrasing
  - prohibited content

This is the single most reliable way to make the output feel consistent across sections.

### 6) Citations / traceability

If auditability matters:

- instruct the model to add bracketed citations like `[Doc:filename]` after claims
- or return a second field listing which documents were used

This helps clinicians trust the text.

## Hyperparameter tuning (Ollama options)

Hyperparameters currently live in `backend/services/ollama_client.py` in the POST body under `options`.

### Temperature

- Lower temperature:
  - more consistent, less creative
  - recommended for clinical writing
- Higher temperature:
  - more varied phrasing
  - increases hallucination risk

Suggested starting points:

- section drafting: `temperature=0.2–0.5`
- paraphrasing / polishing: `temperature=0.3–0.7`

### Context window (`num_ctx`) and truncation strategy

Clinical reports + documents can exceed model context.

Options:

- Set larger context (`num_ctx`) for models that support it.
- Implement summarization / chunking before prompting.
- Add a “document selection” step (see RAG section below).

### Output length (`num_predict`)

- Too low: outputs cut off mid-sentence.
- Too high: increased latency and ram usage.

A good pattern is:

- set a per-section `max_tokens` based on section type
- add server-side post-checks (if output ends mid-sentence, auto-continue once)

### Seed and repeat penalty

Consider setting:

- `seed` for reproducibility during testing
- `repeat_penalty` to reduce loops

## Model improvements (within Ollama)

### Use instruction-tuned models

Many “base” models are weak at following constraints.

Try instruction models that are still reasonably small:

- `phi3:mini` (if available in your environment)
- `mistral:instruct` / `llama3:instruct` (larger)

Tradeoffs:

- better instruction following
- larger disk and higher latency

### Use custom Modelfiles

This repo already contains modelfiles under `modelfiles/`.

You can create a custom Ollama model variant with:

- a tighter clinical system prompt
- default parameters (`temperature`, `num_ctx`, etc.)

Then update backend to call that model name.

### Quantization choice matters

- Smaller quant (Q4) runs on more machines but may reduce fidelity.
- Higher quant (Q6/Q8) improves writing quality but increases RAM/CPU.

## Retrieval augmentation (RAG) without internet

A major driver of hallucinations is asking a small model to reason over too much raw text.

Offline RAG approach:

1) chunk documents at upload time
2) embed chunks locally (e.g., sentence-transformers)
3) retrieve top-k chunks per section prompt
4) provide only the top-k chunks to the LLM

Benefits:

- better factual grounding
- much smaller context
- better speed

Costs:

- bundling an embedding model
- extra storage and indexing

## Post-processing and validation

Even without RAG, you can improve reliability with post-checks.

Examples:

- ensure the output does not contain banned phrases (e.g., “as an AI language model”)
- ensure the output is not empty
- ensure it does not include headers when it shouldn’t
- ensure it doesn’t add diagnoses unless allowed

If validation fails:

- retry with a stricter prompt
- or show a UI error explaining what failed

## Evaluation strategy (offline)

To improve quality iteratively:

- create a small set of anonymized test cases:
  - sample templates
  - sample inputs
  - sample documents
- define expected properties:
  - no hallucinated scores
  - correct tone
  - uses provided info
  - consistent formatting

Track:

- latency
- output length
- subjective quality rating by a clinician

You can add a dev-only endpoint to run “golden prompts” and save outputs.

## Alternative backend: GGUF / llama.cpp instead of Ollama

Ollama is convenient, but bundling and model management can be heavy.

A common alternative for “single-binary” offline apps is:

- ship a `.gguf` model file
- run inference directly from Python via llama.cpp bindings

### Pros

- fewer moving parts (no separate Ollama daemon)
- predictable model file location
- easier to lock versions and avoid port conflicts

### Cons

- more engineering work to implement
- performance and compatibility tuning on Windows
- you must implement:
  - prompt formatting
  - sampling parameters
  - streaming (optional)
  - model loading lifecycle

### Migration path

1) abstract the inference client behind an interface (Ollama vs GGUF)
2) implement a GGUF backend
3) add a config flag/env var to select backend
4) update packaging (bundle `.gguf` and native deps)

## Practical next steps (recommended order)

1) Prompt constraints + placeholders (reduce hallucination risk)
2) Lower temperature defaults for clinical generation
3) Section-specific prompt templates
4) Output validation and automatic retry for common failure modes
5) Optional: RAG for source grounding
6) Optional: experiment with a stronger instruction model
7) Optional: consider GGUF migration if packaging/ports are a long-term pain
