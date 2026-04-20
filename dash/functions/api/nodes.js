const CLOUDFLARE_API_BASE = 'https://api.cloudflare.com/client/v4';

function json(data, init = {}) {
  const headers = new Headers(init.headers || {});
  headers.set('content-type', 'application/json; charset=utf-8');
  headers.set('cache-control', 'no-store');
  return new Response(JSON.stringify(data, null, 2), {
    ...init,
    headers,
  });
}

function mapTunnelToNode(tunnel) {
  const status = (tunnel.status || 'unknown').toLowerCase();
  const connections = Array.isArray(tunnel.connections) ? tunnel.connections : [];
  const activeConnections = connections.filter((conn) => !conn.is_pending_reconnect).length;

  return {
    id: tunnel.id,
    name: tunnel.name || 'Unnamed tunnel',
    type: tunnel.tun_type || 'cfd_tunnel',
    online: status === 'healthy' || status === 'degraded',
    status,
    createdAt: tunnel.created_at || null,
    activeAt: tunnel.conns_active_at || null,
    inactiveAt: tunnel.conns_inactive_at || null,
    activeConnections,
    connectionCount: connections.length,
    metadata: tunnel.metadata || null,
  };
}

async function fetchCloudflareTunnels(env) {
  const accountId = env.CLOUDFLARE_ACCOUNT_ID;
  const apiToken = env.CLOUDFLARE_API_TOKEN;

  if (!accountId || !apiToken) {
    throw new Error(
      'Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN. Add them as Pages environment variables.'
    );
  }

  const response = await fetch(`${CLOUDFLARE_API_BASE}/accounts/${accountId}/cfd_tunnel`, {
    headers: {
      Authorization: `Bearer ${apiToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Cloudflare API request failed (${response.status}): ${text}`);
  }

  const payload = await response.json();

  if (!payload.success) {
    throw new Error(payload.errors?.map((e) => e.message).join('; ') || 'Cloudflare API returned success=false');
  }

  const tunnels = Array.isArray(payload.result) ? payload.result : [];
  const nodes = tunnels
    .filter((tunnel) => !tunnel.deleted_at)
    .map(mapTunnelToNode)
    .sort((a, b) => a.name.localeCompare(b.name));

  return {
    generatedAt: new Date().toISOString(),
    summary: {
      total: nodes.length,
      online: nodes.filter((node) => node.online).length,
      offline: nodes.filter((node) => !node.online).length,
    },
    nodes,
  };
}

export async function onRequestGet(context) {
  try {
    const data = await fetchCloudflareTunnels(context.env);
    return json(data);
  } catch (error) {
    return json(
      {
        error: 'Failed to load nodes from Cloudflare.',
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
