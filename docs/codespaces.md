# GitHub Codespaces

## Start

1. Open the repository in GitHub.
2. Choose **Code → Codespaces → Create codespace on main**.
3. Wait for the container to build.
4. Run `docker compose up --build`.
5. Open forwarded port `3000`.

## Development loop

```bash
git status
git add .
git commit -m "feat: ..."
git push
```

The `.devcontainer` forwards ports 3000 and 8000 so the browser can reach the app and API documentation from the Codespace.
