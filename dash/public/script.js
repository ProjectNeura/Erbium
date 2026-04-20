const state = {
  nodes: [],
};

function byId(id) {
  return document.getElementById(id);
}

const elements = {
  totalCount: null,
  onlineCount: null,
  offlineCount: null,
  generatedAt: null,
  nodesGrid: null,
  message: null,
  searchInput: null,
  statusFilter: null,
  refreshButton: null,
  nodeCardTemplate: null,
};

function initElements() {
  elements.totalCount = byId('totalCount');
  elements.onlineCount = byId('onlineCount');
  elements.offlineCount = byId('offlineCount');
  elements.generatedAt = byId('generatedAt');
  elements.nodesGrid = byId('nodesGrid');
  elements.message = byId('message');
  elements.searchInput = byId('searchInput');
  elements.statusFilter = byId('statusFilter');
  elements.refreshButton = byId('refreshButton');
  elements.nodeCardTemplate = byId('nodeCardTemplate');
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function setMessage(text, isError = false) {
  if (!elements.message) return;
  elements.message.textContent = text;
  elements.message.classList.toggle('hidden', !text);
  elements.message.style.borderColor = isError ? 'rgba(255, 107, 107, 0.3)' : 'rgba(255, 255, 255, 0.08)';
}

function getFilteredNodes() {
  const query = elements.searchInput?.value?.trim().toLowerCase() ?? '';
  const statusFilter = elements.statusFilter?.value ?? 'all';

  return state.nodes.filter((node) => {
    const name = String(node.name || '');
    const matchesQuery = !query || name.toLowerCase().includes(query);
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'online' && node.online) ||
      (statusFilter === 'offline' && !node.online);

    return matchesQuery && matchesStatus;
  });
}

function buildNodeLinks(nodeName) {
  const match = String(nodeName || '').match(/^\s*([A-Za-z0-9]+).*?-\s*([A-Za-z0-9]+)\s*$/);
  if (!match) return [];

  const cluster = match[1].toLowerCase();
  const nodeCode = match[2].toLowerCase();
  const slug = `${nodeCode}-${cluster}`;

  return [
    { label: 'SSH Tunnel', href: `https://${slug}.projectneura.org` },
    { label: 'JupyterLab', href: `https://jupyter-${slug}.projectneura.org` },
    { label: 'Node Dashboard', href: `https://node-${slug}.projectneura.org/dash` },
  ];
}

function renderNodeLinks(container, node) {
  if (!container) return;
  container.replaceChildren();

  if (!node.online) {
    container.classList.add('hidden');
    return;
  }

  const links = buildNodeLinks(node.name);
  if (!links.length) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');

  for (const link of links) {
    const anchor = document.createElement('a');
    anchor.className = 'link-button';
    anchor.href = link.href;
    anchor.target = '_blank';
    anchor.rel = 'noreferrer noopener';
    anchor.textContent = link.label;
    container.appendChild(anchor);
  }
}

function renderNodes() {
  if (!elements.nodesGrid) {
    throw new Error('Missing #nodesGrid element in index.html');
  }

  const filteredNodes = getFilteredNodes();
  elements.nodesGrid.replaceChildren();

  if (!filteredNodes.length) {
    setMessage('No nodes match the current filters.');
    return;
  }

  setMessage('');

  for (const node of filteredNodes) {
    if (elements.nodeCardTemplate?.content) {
      const fragment = elements.nodeCardTemplate.content.cloneNode(true);
      const nameEl = fragment.querySelector('.node-name');
      const typeEl = fragment.querySelector('.node-type');
      const statusPill = fragment.querySelector('.status-pill');
      const connectionCountEl = fragment.querySelector('.connection-count');
      const activeAtEl = fragment.querySelector('.active-at');
      const inactiveAtEl = fragment.querySelector('.inactive-at');
      const nodeIdEl = fragment.querySelector('.node-id');
      const linksContainer = fragment.querySelector('.node-links');

      if (nameEl) nameEl.textContent = node.name || 'Unnamed node';
      if (typeEl) typeEl.textContent = node.type || 'Tunnel';

      if (statusPill) {
        statusPill.textContent = node.status || 'unknown';
        statusPill.classList.add(node.status === 'degraded' ? 'degraded' : node.online ? 'online' : 'offline');
      }

      if (connectionCountEl) {
        connectionCountEl.textContent = `${node.activeConnections ?? 0} active / ${node.connectionCount ?? 0} total`;
      }
      if (activeAtEl) activeAtEl.textContent = formatDate(node.activeAt);
      if (inactiveAtEl) inactiveAtEl.textContent = formatDate(node.inactiveAt);
      if (nodeIdEl) nodeIdEl.textContent = node.id || '—';

      renderNodeLinks(linksContainer, node);
      elements.nodesGrid.appendChild(fragment);
      continue;
    }

    const card = document.createElement('article');
    card.className = 'node-card';
    card.innerHTML = `
      <div class="node-header">
        <div>
          <h2 class="node-name"></h2>
          <p class="node-type"></p>
        </div>
        <span class="status-pill"></span>
      </div>
      <dl class="node-details">
        <div><dt>Connections</dt><dd class="connection-count"></dd></div>
        <div><dt>Active at</dt><dd class="active-at"></dd></div>
        <div><dt>Inactive at</dt><dd class="inactive-at"></dd></div>
        <div><dt>ID</dt><dd class="node-id"></dd></div>
      </dl>
      <div class="node-links hidden" aria-label="Node links"></div>
    `;

    card.querySelector('.node-name').textContent = node.name || 'Unnamed node';
    card.querySelector('.node-type').textContent = node.type || 'Tunnel';
    const statusPill = card.querySelector('.status-pill');
    statusPill.textContent = node.status || 'unknown';
    statusPill.classList.add(node.status === 'degraded' ? 'degraded' : node.online ? 'online' : 'offline');
    card.querySelector('.connection-count').textContent = `${node.activeConnections ?? 0} active / ${node.connectionCount ?? 0} total`;
    card.querySelector('.active-at').textContent = formatDate(node.activeAt);
    card.querySelector('.inactive-at').textContent = formatDate(node.inactiveAt);
    card.querySelector('.node-id').textContent = node.id || '—';
    renderNodeLinks(card.querySelector('.node-links'), node);
    elements.nodesGrid.appendChild(card);
  }
}

function renderSummary(summary = {}, generatedAt) {
  if (elements.totalCount) elements.totalCount.textContent = summary.total ?? 0;
  if (elements.onlineCount) elements.onlineCount.textContent = summary.online ?? 0;
  if (elements.offlineCount) elements.offlineCount.textContent = summary.offline ?? 0;
  if (elements.generatedAt) elements.generatedAt.textContent = formatDate(generatedAt);
}

async function loadNodes() {
  if (elements.refreshButton) elements.refreshButton.disabled = true;
  setMessage('Loading nodes…');

  try {
    const response = await fetch('/api/nodes');
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || payload.error || 'Unknown error');
    }

    state.nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
    renderSummary(payload.summary, payload.generatedAt);
    renderNodes();
  } catch (error) {
    setMessage(`Could not load nodes: ${error.message}`, true);
    if (elements.nodesGrid) {
      elements.nodesGrid.replaceChildren();
    }
  } finally {
    if (elements.refreshButton) elements.refreshButton.disabled = false;
  }
}

function init() {
  initElements();

  elements.searchInput?.addEventListener('input', renderNodes);
  elements.statusFilter?.addEventListener('change', renderNodes);
  elements.refreshButton?.addEventListener('click', loadNodes);

  loadNodes();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}
