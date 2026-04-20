# Cloudflare Nodes Dashboard

A Cloudflare Pages app that reads your Cloudflare Tunnel inventory and shows which nodes are online.

## What it does

- Calls the Cloudflare API from a Pages Function, so your API token stays server-side.
- Lists all Cloudflare Tunnels (`/accounts/{account_id}/cfd_tunnel`).
- Marks each node as online or offline based on the tunnel status.
- Shows connection counts and timestamps.
- For online nodes, generates SSH, JupyterLab, and dashboard links from the tunnel name.
- Supports search and status filtering in the UI.

## Required environment variables

Add these in your Cloudflare Pages project settings:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`

Your API token should have read access for Cloudflare Tunnel / Cloudflare One connectors.

## Local development

```bash
npm install
npx wrangler pages dev public
```

## Deploy to Cloudflare Pages

### Option 1: Git-based deployment

1. Push this project to GitHub.
2. In Cloudflare, create a new Pages project from that repository.
3. Use these build settings:
   - Build command: leave empty
   - Build output directory: `public`
4. Add the two environment variables above.
5. Deploy.

### Option 2: Wrangler deploy

```bash
npm install
npx wrangler pages deploy public --project-name cloudflare-nodes-dashboard
```

Then add the same environment variables in the Pages dashboard.

## Project structure

```text
public/
  index.html
  script.js
  styles.css
functions/
  api/
    nodes.js
```

## Notes

- The dashboard treats `healthy` and `degraded` as online.
- It treats `down` and `inactive` as offline.
- The app filters out deleted tunnels.

## Tunnel link naming

For tunnel names like `Erbium Gateway A - 4090` or `Erbium Gateway B - 5090`, the dashboard generates:

- `https://4090-erbium.projectneura.org`
- `https://jupyter-4090-erbium.projectneura.org`
- `https://node-4090-erbium.projectneura.org/dash`

It uses the first word in the tunnel name as the cluster slug (`erbium`) and the suffix after the last dash as the node code (`4090`, `5090`, etc.). Offline nodes do not show these buttons.
