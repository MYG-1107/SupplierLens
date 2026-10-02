# Product Scope — SupplierLens v0.1

## User
Procurement, finance, operations, and SME owners who need to onboard a new supplier.

## Core job-to-be-done
Before making a purchasing commitment, assemble available supplier evidence in one place, detect contradictions, and identify items that need human review.

## Non-goals for v0.1
- Certifying a supplier as genuine
- Determining legal liability
- Automatically approving payments
- Scraping protected government portals
- Making a fraud accusation from weak evidence

## Evidence model
Each finding should point back to a source item. The UI should distinguish:
1. Source evidence supplied by the user or a permitted external connector.
2. Deterministic software checks.
3. ML-derived signals.
4. LLM-generated explanation.

## Product metrics to measure later
- Time to complete supplier onboarding
- Percentage of supplier records with complete identity evidence
- Human review rate
- False-positive rate for consistency flags
- Mean time from supplier submission to procurement decision
