# AI/ML roadmap

## Stage 1 — document intelligence

Add OCR and document-layout extraction for PDF/image evidence. Normalize extracted fields into the existing `DocumentEvidence` contract.

## Stage 2 — entity resolution

Use character similarity as the baseline, then evaluate multilingual embeddings to resolve legal names, trade names and account names. Keep a human-review threshold.

## Stage 3 — anomaly detection

Build a labelled synthetic/evaluation dataset containing normal and inconsistent supplier evidence. Compare interpretable baselines such as logistic regression, isolation forest and gradient boosting.

## Stage 4 — RAG

Index evidence snippets, supplier policy documents and verification guidance. Answers should cite the evidence chunks used.

## Stage 5 — LLM orchestration

Use the LLM only after deterministic checks and retrieval. Return structured claims, source references, uncertainty and suggested follow-up actions.

## Stage 6 — continuous monitoring

Track changes to supplier attributes and new evidence events. Trigger re-verification when material changes occur.
