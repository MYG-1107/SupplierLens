# GitHub Codespaces

## Start

```bash
docker compose down -v
docker compose up --build
```

The `web` service explicitly builds the `dev` Docker target so its Next.js dependencies are fresh and available to `npm run dev`. Versioned volumes are used for `node_modules` and `.next` to avoid stale state from earlier SupplierLens images.

Open the forwarded port **3000** for the web app and **8000** for the FastAPI docs.

## Verify

```bash
curl http://localhost:8000/health
```

Then run a supplier verification from the UI.
