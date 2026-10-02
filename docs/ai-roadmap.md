# AI / ML Roadmap

## Step 1 — Document extraction
Use OCR and structured extraction to convert uploaded PDFs/images into fields:
- Legal name
- Trade name
- GSTIN
- Address
- Bank account name
- Contact details
- Document date

## Step 2 — Entity resolution
Create embeddings for supplier names and addresses. Combine semantic similarity with deterministic normalization and business rules.

## Step 3 — Anomaly detection
Train a model using synthetic and eventually consented historical procurement data. Candidate features include mismatch counts, unusual field combinations, evidence freshness, domain age signals where legally and technically available, and supplier-history patterns.

Do not train a fraud classifier until there is a defensible labeled dataset.

## Step 4 — RAG
Store normalized evidence and source metadata. Retrieve the relevant evidence before producing an explanation.

## Step 5 — Explainable LLM
Prompt the LLM to summarize only retrieved evidence, disclose uncertainty, and list next verification steps. Never allow it to create unsupported supplier facts.

## Step 6 — Evaluation
Create a test set with:
- clean suppliers
- harmless name variations
- genuine bank/legal-name differences
- document OCR errors
- address abbreviations
- deliberate synthetic inconsistencies

Measure precision/recall for each individual signal rather than only an overall score.
