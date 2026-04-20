const state = {
  nodes: [],
};

const elements = {
  totalCount: document.getElementById('totalCount'),
  onlineCount: document.getElementById('onlineCount'),
  offlineCount: document.getElementById('offlineCount'),
  generatedAt: document.getElementById('generatedAt'),
  nodesGrid: document.getElementById('nodesGrid'),
  message: document.getElementById('message'),
  searchInput: document.getElementById('searchInput'),
  statusFilter: document.getElementById('statusFilter'),
  refreshButton: document.getElementById('refreshButton'),
  nodeCardTemplate: document.getElementById('nodeCardTemplate'),
};

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
  elements.message.textContent = text;
  elements.message.classList.toggle('hidden', !text);
  elements.message.style.borderColor = isError ? 'rgba(255, 107, 107, 0.3)' : 'rgba(255, 255, 255, 0.08)';
}

function getFilteredNodes() {
  const query = elements.searchInput.value.trim().toLowerCase();
  const statusFilter = elements.statusFilter.value;

  return state.nodes.filter((node) => {
    const matchesQuery = !query || node.name.toLowerCase().includes(query);
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'online' && node.online) ||
      (statusFilter === 'offline' && !node.online);

    return matchesQuery && matchesStatus;
  });
}

function buildNodeLinks(nodeName) {
  const match = nodeName.match(/^\s*([A-Za-z0-9]+).*?-\s*([A-Za-z0-9]+)\s*$/);
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
  const filteredNodes = getFilteredNodes();
  elements.nodesGrid.replaceChildren();

  if (!filteredNodes.length) {
    setMessage('No nodes match the current filters.');
    return;
  }

  setMessage('');

  for (const node of filteredNodes) {
    const fragment = elements.nodeCardTemplate.content.cloneNode(true);
    fragment.querySelector('.node-name').textContent = node.name;
    fragment.querySelector('.node-type').textContent = node.type;

    const statusPill = fragment.querySelector('.status-pill');
    statusPill.textContent = node.status;
    statusPill.classList.add(node.status === 'degraded' ? 'degraded' : node.online ? 'online' : 'offline');

    fragment.querySelector('.connection-count').textContent = `${node.activeConnections} active / ${node.connectionCount} total`;
    fragment.querySelector('.active-at').textContent = formatDate(node.activeAt);
    fragment.querySelector('.inactive-at').textContent = formatDate(node.inactiveAt);
    fragment.querySelector('.node-id').textContent = node.id || '—';

    const linksContainer = fragment.querySelector('.node-links');
    renderNodeLinks(linksContainer, node);

    elements.nodesGrid.appendChild(fragment);
  }
}

function renderSummary(summary, generatedAt) {
  elements.totalCount.textContent = summary.total;
  elements.onlineCount.textContent = summary.online;
  elements.offlineCount.textContent = summary.offline;
  elements.generatedAt.textContent = formatDate(generatedAt);
}

async function loadNodes() {
  elements.refreshButton.disabled = true;
  setMessage('Loading nodes…');

  try {
    const response = await fetch('/api/nodes');
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || payload.error || 'Unknown error');
    }

    state.nodes = payload.nodes || [];
    renderSummary(payload.summary, payload.generatedAt);
    renderNodes();
  } catch (error) {
    setMessage(`Could not load nodes: ${error.message}`, true);
    elements.nodesGrid.replaceChildren();
  } finally {
    elements.refreshButton.disabled = false;
  }
}

elements.searchInput.addEventListener('input', renderNodes);
elements.statusFilter.addEventListener('change', renderNodes);
elements.refreshButton.addEventListener('click', loadNodes);

loadNodes();
