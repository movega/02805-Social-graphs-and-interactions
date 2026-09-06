const svg = d3.select('#chart');
const tooltip = d3.select('#tooltip');
const detailName = document.getElementById('detailName');
const detailUndirected = document.getElementById('detailUndirected');
const detailIncoming = document.getElementById('detailIncoming');
const detailOutgoing = document.getElementById('detailOutgoing');
const detailBalance = document.getElementById('detailBalance');
const detailArchetype = document.getElementById('detailArchetype');
const detailConnectedRank = document.getElementById('detailConnectedRank');
const detailPopularityRank = document.getElementById('detailPopularityRank');
const detailSummary = document.getElementById('detailSummary');
const chartIntro = document.getElementById('chartIntro');
const revealButton = document.getElementById('revealButton');
const surpriseButton = document.getElementById('surpriseButton');
const characterSearch = document.getElementById('characterSearch');
const characterOptions = document.getElementById('characterOptions');
const connectedBar = document.getElementById('connectedBar');
const incomingBar = document.getElementById('incomingBar');

const state = {
  data: [],
  reveal: false,
  selected: null,
  filtered: null,
  margin: { top: 32, right: 46, bottom: 54, left: 62 },
};

const width = 920;
const height = 620;

const personalityStyles = {
  celebrities: { label: 'Celebrities', color: '#70b7ff' },
  connectors: { label: 'Connectors', color: '#ffb347' },
  socialites: { label: 'Socialites', color: '#d4a6ff' },
  outsiders: { label: 'Outsiders', color: '#8d9aa8' },
};

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function buildScales(data) {
  const maxOut = d3.max(data, d => d.out_degree) || 1;
  const maxIn = d3.max(data, d => d.in_degree) || 1;
  const maxUndirected = d3.max(data, d => d.undirected_degree) || 1;

  const x = d3.scaleLinear().domain([0, maxOut * 1.12]).range([state.margin.left, width - state.margin.right]);
  const y = d3.scaleLinear().domain([0, maxIn * 1.12]).range([height - state.margin.bottom, state.margin.top]);

  const rScale = d3.scaleLinear().domain([0, maxUndirected]).range([3.5, 16]);

  return { x, y, rScale };
}

function makeRankings(data) {
  const connectedness = [...data].sort((a, b) => b.undirected_degree - a.undirected_degree);
  const popularity = [...data].sort((a, b) => b.in_degree - a.in_degree);

  connectedness.forEach((d, i) => { d.connectednessRank = i + 1; });
  popularity.forEach((d, i) => { d.popularityRank = i + 1; });

  return { connectedness, popularity };
}

function percentile(values, quantile) {
  return d3.quantile([...values].sort(d3.ascending), quantile) || 0;
}

function assignPersonalities(data) {
  const inThreshold = percentile(data.map(d => d.in_degree), 0.8);
  const outThreshold = percentile(data.map(d => d.out_degree), 0.8);
  const totalThreshold = percentile(data.map(d => d.total_directed_degree), 0.2);

  data.forEach(d => {
    if (d.total_directed_degree <= totalThreshold) {
      d.personality = 'outsiders';
    } else if (d.in_degree >= inThreshold && d.out_degree >= outThreshold) {
      d.personality = 'socialites';
    } else if (d.in_degree > d.out_degree) {
      d.personality = 'celebrities';
    } else {
      d.personality = 'connectors';
    }
  });
}

function updateDetailPanel(d) {
  if (!d) {
    detailName.textContent = 'Select a character';
    detailUndirected.textContent = '—';
    detailIncoming.textContent = '—';
    detailOutgoing.textContent = '—';
    detailBalance.textContent = '—';
    detailArchetype.textContent = '—';
    detailConnectedRank.textContent = '—';
    detailPopularityRank.textContent = '—';
    connectedBar.style.width = '0%';
    incomingBar.style.width = '0%';
    detailSummary.textContent = 'Choose a node to see how its network position differs from its popularity.';
    return;
  }

  const combined = d.total_directed_degree || 1;
  const connectedPercent = (d.connectednessRank / state.data.length) * 100;
  const popularityPercent = (d.popularityRank / state.data.length) * 100;

  detailName.textContent = d.character;
  detailUndirected.textContent = d.undirected_degree;
  detailIncoming.textContent = d.in_degree;
  detailOutgoing.textContent = d.out_degree;
  detailBalance.textContent = d.balance;
  detailArchetype.textContent = personalityStyles[d.personality].label;
  detailConnectedRank.textContent = `#${d.connectednessRank}`;
  detailPopularityRank.textContent = `#${d.popularityRank}`;
  connectedBar.style.width = `${clamp(100 - connectedPercent, 6, 100)}%`;
  incomingBar.style.width = `${clamp(100 - popularityPercent, 6, 100)}%`;

  let summary = '';
  if (d.personality === 'celebrities') {
    summary = 'Mostly receives attention from the rest of the network.';
  } else if (d.personality === 'connectors') {
    summary = 'Links outward much more than it is linked back to.';
  } else if (d.personality === 'socialites') {
    summary = 'Highly embedded in both directions.';
  } else {
    summary = 'Peripheral in this Marvel Wikipedia network.';
  }

  detailSummary.textContent = summary;
}

function buildAxes(scales) {
  const g = svg.append('g');

  const xAxis = d3.axisBottom(scales.x).ticks(8).tickSizeOuter(0);
  const yAxis = d3.axisLeft(scales.y).ticks(8).tickSizeOuter(0);

  g.append('g')
    .attr('transform', `translate(0, ${height - state.margin.bottom})`)
    .call(xAxis)
    .call(g => g.select('.domain').attr('stroke', 'rgba(255,255,255,0.25)'))
    .call(g => g.selectAll('.tick line').attr('stroke', 'rgba(255,255,255,0.12)'))
    .call(g => g.selectAll('.tick text').attr('fill', '#b5c7d9'));

  g.append('g')
    .attr('transform', `translate(${state.margin.left}, 0)`)
    .call(yAxis)
    .call(g => g.select('.domain').attr('stroke', 'rgba(255,255,255,0.25)'))
    .call(g => g.selectAll('.tick line').attr('stroke', 'rgba(255,255,255,0.12)'))
    .call(g => g.selectAll('.tick text').attr('fill', '#b5c7d9'));

  g.append('line')
    .attr('x1', state.margin.left)
    .attr('x2', width - state.margin.right)
    .attr('y1', height - state.margin.bottom)
    .attr('y2', height - state.margin.bottom)
    .attr('class', 'axis-line');

  g.append('line')
    .attr('x1', state.margin.left)
    .attr('x2', state.margin.left)
    .attr('y1', state.margin.top)
    .attr('y2', height - state.margin.bottom)
    .attr('class', 'axis-line');

  g.append('text')
    .attr('class', 'axis-label')
    .attr('x', (width - state.margin.left - state.margin.right) / 2 + state.margin.left)
    .attr('y', height - 12)
    .attr('text-anchor', 'middle')
    .text('Outgoing links (out-degree) →');

  g.append('text')
    .attr('class', 'axis-label')
    .attr('transform', 'rotate(-90)')
    .attr('x', -(height - state.margin.top - state.margin.bottom) / 2 - state.margin.top)
    .attr('y', 18)
    .attr('text-anchor', 'middle')
    .text('Incoming links (in-degree) →');

  return g;
}

function buildGrid(scales) {
  const grid = svg.append('g');
  const xTicks = scales.x.ticks(8);
  const yTicks = scales.y.ticks(8);

  xTicks.forEach(value => {
    grid.append('line')
      .attr('class', 'grid-line')
      .attr('x1', scales.x(value))
      .attr('x2', scales.x(value))
      .attr('y1', state.margin.top)
      .attr('y2', height - state.margin.bottom);
  });

  yTicks.forEach(value => {
    grid.append('line')
      .attr('class', 'grid-line')
      .attr('x1', state.margin.left)
      .attr('x2', width - state.margin.right)
      .attr('y1', scales.y(value))
      .attr('y2', scales.y(value));
  });

  const diagonalLine = d3.line();
  const data = [
    [0, 0],
    [scales.x.domain()[1], scales.y.domain()[1]],
  ];

  grid.append('path')
    .datum(data)
    .attr('class', 'diagonal-line')
    .attr('d', diagonalLine)
    .attr('fill', 'none')
    .style('opacity', state.reveal ? 0.9 : 0.25);

  // region labels
  const labelGroup = svg.append('g');
  labelGroup.append('text')
    .attr('class', 'region-label')
    .attr('x', width * 0.2)
    .attr('y', state.margin.top + 18)
    .attr('opacity', state.reveal ? 0.75 : 0.15)
    .text('The celebrities');

  labelGroup.append('text')
    .attr('class', 'region-label')
    .attr('x', width * 0.68)
    .attr('y', state.margin.top + 18)
    .attr('opacity', state.reveal ? 0.75 : 0.15)
    .text('The power players');

  labelGroup.append('text')
    .attr('class', 'region-label')
    .attr('x', width * 0.18)
    .attr('y', height - 120)
    .attr('opacity', state.reveal ? 0.75 : 0.15)
    .text('The connectors');

  // subtle explanatory labels
  const guideText = svg.append('g');
  guideText.append('text')
    .attr('x', width * 0.56)
    .attr('y', state.margin.top + 64)
    .attr('fill', '#dfeaf8')
    .attr('font-size', 18)
    .attr('font-weight', 700)
    .attr('opacity', state.reveal ? 1 : 0.15)
    .text('More talked about');

  guideText.append('text')
    .attr('x', width * 0.18)
    .attr('y', height - 148)
    .attr('fill', '#dfeaf8')
    .attr('font-size', 18)
    .attr('font-weight', 700)
    .attr('opacity', state.reveal ? 1 : 0.15)
    .text('Talks about more characters');
}

function renderChart() {
  svg.selectAll('*').remove();
  const { x, y, rScale } = buildScales(state.data);
  buildGrid({ x, y });
  buildAxes({ x, y });

  const points = svg.append('g');
  const selectedName = state.selected ? state.selected.character : null;

  points.selectAll('circle')
    .data(state.data)
    .join('circle')
    .attr('class', d => `node ${d.character === selectedName ? 'selected' : ''}`)
    .attr('cx', d => x(d.out_degree))
    .attr('cy', d => y(d.in_degree))
    .attr('r', d => clamp(rScale(d.undirected_degree), 3.5, 16))
    .attr('fill', d => personalityStyles[d.personality].color)
    .attr('opacity', d => (selectedName && d.character !== selectedName ? 0.18 : 0.82))
    .on('mouseenter', (event, d) => {
      tooltip
        .html(`
          <strong>${d.character}</strong><br>
          Connected to: ${d.undirected_degree}<br>
          Incoming links: ${d.in_degree}<br>
          Outgoing links: ${d.out_degree}
        `)
        .classed('hidden', false)
        .style('left', `${event.clientX + 15}px`)
        .style('top', `${event.clientY + 15}px`);
    })
    .on('mousemove', (event) => {
      tooltip
        .style('left', `${event.clientX + 15}px`)
        .style('top', `${event.clientY + 15}px`);
    })
    .on('mouseleave', () => tooltip.classed('hidden', true))
    .on('click', (_, d) => {
      state.selected = d;
      d3.selectAll('.node').classed('selected', node => node.character === d.character);
      d3.selectAll('.node').classed('dimmed', node => node.character !== d.character && selectedName !== null);
      updateDetailPanel(d);
    });

  const selectedNode = state.selected ? state.data.find(d => d.character === state.selected.character) : null;
  if (selectedNode) updateDetailPanel(selectedNode);
  else updateDetailPanel(null);
}

function syncRevealState() {
  const opacity = state.reveal ? 0.9 : 0.15;
  d3.selectAll('.region-label').attr('opacity', opacity);
  d3.selectAll('.diagonal-line').style('opacity', state.reveal ? 0.9 : 0.25);
  d3.selectAll('.node').style('opacity', d => {
    if (!state.reveal && !state.selected) return 0.82;
    if (state.selected && d.character !== state.selected.character) return 0.18;
    return 0.82;
  });
  chartIntro.textContent = state.reveal
    ? 'The diagonal separates attention received from attention given.'
    : 'Big dots look important. But are they popular?';
}

function refreshSearchOptions(data) {
  characterOptions.innerHTML = '';
  data.forEach(d => {
    const option = document.createElement('option');
    option.value = d.character;
    characterOptions.appendChild(option);
  });
}

function highlightCharacter(name) {
  const target = state.data.find(d => d.character === name);
  if (!target) return;
  state.selected = target;
  d3.selectAll('.node').classed('selected', d => d.character === name);
  d3.selectAll('.node').classed('dimmed', d => d.character !== name && state.selected !== null);
  updateDetailPanel(target);
}

function chooseSurpriseCharacter() {
  const scored = state.data
    .map(d => ({ ...d, surprise: Math.abs(d.balance) / Math.sqrt(d.total_directed_degree + 1) }))
    .sort((a, b) => b.surprise - a.surprise);

  const picked = scored.slice(0, 10)[Math.floor(Math.random() * Math.min(10, scored.length))];
  if (picked) {
    highlightCharacter(picked.character);
    characterSearch.value = picked.character;
  }
}

async function loadData() {
  const response = await fetch('assets/data/marvel_nodes.json');
  const data = await response.json();
  state.data = data;
  assignPersonalities(data);
  makeRankings(data);
  refreshSearchOptions(data);
  renderChart();
  syncRevealState();
}

revealButton.addEventListener('click', () => {
  state.reveal = !state.reveal;
  revealButton.textContent = state.reveal ? 'Hide direction ←' : 'Reveal direction →';
  syncRevealState();
});

surpriseButton.addEventListener('click', chooseSurpriseCharacter);

characterSearch.addEventListener('change', (event) => {
  const value = event.target.value.trim();
  if (value) highlightCharacter(value);
});

loadData();
