# Security

SupplierLens handles supplier and procurement evidence. Treat uploaded files as sensitive business data.

- Never commit secrets or production documents.
- Keep API keys in environment variables or a secrets manager.
- Validate upload extensions and size limits.
- Add authentication and authorization before multi-user deployment.
- Prefer private object storage for production documents.
- Keep source evidence and model output distinguishable.
- Do not treat the AI output as a certification, legal determination, or sole basis for a payment decision.
