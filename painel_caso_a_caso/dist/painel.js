// ---------- constantes visuais (identidade do banner) ----------
const FONTE = '"IBM Plex Sans", Arial, sans-serif';
const COR = {
  tinta: '#1F2328', tinta2: '#4A5261', tinta3: '#6B7383', grade: '#E3E7EE', trilho: '#EEF1F6',
  c1: '#7189B0', c2: '#3E5A8A', d: '#182B4E', ref: '#A9B1BE', faixa: '#59606B',
  perigo: '#9E3B3B', perigoClaro: '#D9877A', menores: '#2A9D5C', fronteira: '#1F4E8C',
  legit: '#6F7785', legitClaro: '#B3B9C3', papel: '#FFFFFF',
};
const COR_COND = { C1: COR.c1, C2: COR.c2, D: COR.d };
const HALO = { stroke: '#FFFFFF', lineWidth: 4, strokeOpacity: 1, lineJoin: 'round' };
const SEM = { animate: false, tooltip: false };

const pct = (v, casas = 0) => `${v.toFixed(casas).replace('.', ',')}%`;
const dec = (v, casas = 2) => (v < 0 ? '−' : v > 0 ? '+' : '') + Math.abs(v).toFixed(casas).replace('.', ',');
const bloqueadas = ([e, n]) => (n ? (100 * (n - e)) / n : null);
const erradas = ([e, n]) => (n ? (100 * e) / n : null);
const texto = (extra) => ({ fontFamily: FONTE, fillOpacity: 1, ...extra });

function eixoValor(extra = {}) {
  return {
    title: false,
    labelFontFamily: FONTE, labelFontSize: 12, labelFill: COR.tinta3, labelOpacity: 1, labelSpacing: 4,
    line: false, tick: false,
    grid: true, gridStroke: COR.grade, gridLineWidth: 1, gridStrokeOpacity: 1, gridLineDash: [0, 0],
    ...extra,
  };
}

function preparar(el, altura) {
  el.style.height = `${altura}px`;
  el.replaceChildren();
  return new G2.Chart({ container: el, autoFit: true });
}

// ---------- barras horizontais com trilho ----------
// linhas: { chave, codigo, nome, valor, rotulo, fracao, cor, min?, max? }
function specBarras(linhas, op = {}) {
  const max = op.max ?? 100;
  const ticks = op.ticks ?? [0, 25, 50, 75, 100];
  const formato = op.formato ?? ((v) => `${v}%`);
  const estreito = op.largura < 520;
  const faixa = linhas.filter((l) => l.min != null && l.max != null && l.max > l.min);
  const preenchidas = linhas.filter((l) => l.valor > 0);
  return {
    type: 'view',
    theme: 'classic',
    coordinate: { transform: [{ type: 'transpose' }] },
    paddingLeft: op.esquerda ?? 108,
    paddingRight: estreito ? 96 : (op.direita ?? 150),
    paddingTop: 4,
    paddingBottom: 26,
    data: linhas,
    scale: {
      x: { type: 'band', domain: linhas.map((l) => l.chave), paddingInner: 0.45, paddingOuter: 0.25 },
      y: { type: 'linear', domain: [0, max], nice: false, tickMethod: () => ticks },
    },
    axis: { x: false, y: eixoValor({ labelFormatter: formato }) },
    legend: false,
    children: [
      { type: 'interval', encode: { x: 'chave', y: () => max }, style: { fill: COR.trilho, fillOpacity: 1, maxWidth: 28 }, ...SEM },
      {
        type: 'interval', data: preenchidas, encode: { x: 'chave', y: 'valor' },
        style: { fill: (d) => d.cor, fillOpacity: 1, maxWidth: 28 }, animate: false,
        tooltip: { title: (d) => `${d.codigo} ${d.nome}`.trim(), items: [(d) => ({ name: op.nomeValor ?? 'valor', value: `${d.rotulo} · ${d.fracao}${d.extra ? ` · ${d.extra}` : ''}` })] },
      },
      { type: 'interval', data: faixa, encode: { x: 'chave', y: 'min', y1: 'max' }, style: { fill: COR.faixa, fillOpacity: 1, maxWidth: 2, transform: 'translate(0, 22)' }, ...SEM },
      { type: 'text', encode: { x: 'chave', y: () => 0, text: 'codigo' }, style: texto({ fontSize: 17, fontWeight: 700, fill: COR.tinta, textAlign: 'right', textBaseline: 'bottom', dx: -12, dy: 2 }), ...SEM },
      { type: 'text', encode: { x: 'chave', y: () => 0, text: 'nome' }, style: texto({ fontSize: 12.5, fill: COR.tinta2, textAlign: 'right', textBaseline: 'top', dx: -12, dy: 3 }), ...SEM },
      { type: 'text', encode: { x: 'chave', y: () => max, text: 'rotulo' }, style: texto({ fontSize: estreito ? 17 : 22, fontWeight: 700, fill: COR.tinta, textAlign: 'left', textBaseline: 'bottom', dx: 10, dy: 4 }), ...SEM },
      { type: 'text', encode: { x: 'chave', y: () => max, text: 'fracao' }, style: texto({ fontSize: 11.5, fill: COR.tinta2, textAlign: 'left', textBaseline: 'top', dx: 11, dy: 5 }), ...SEM },
    ],
  };
}

function barras(el, linhas, op = {}) {
  const altura = linhas.length * (op.passo ?? 60) + 34;
  const chart = preparar(el, altura);
  const montar = () => specBarras(linhas, { ...op, largura: el.clientWidth });
  chart.options(montar());
  chart.render();
  return { chart, atualizar: () => { chart.options(montar()); chart.render(); } };
}

// ---------- linhas por modelo com pontos (eixo y numérico, controle total) ----------
// linhas: { idx, nome, detalhe, cabecalho? }; series: { cod, cor, rotulo, deslocamento, valor(linha) -> {v, dica} | null }
function specPontos(linhas, series, op = {}) {
  const [x0, x1] = op.dominio ?? [0, 100];
  const ticks = op.ticks ?? [0, 25, 50, 75, 100];
  const formato = op.formato ?? ((v) => `${v}%`);
  const n = linhas.length;
  const destaque = op.destaque ?? 'todas';
  const modelos = linhas.filter((l) => !l.cabecalho);
  const conectores = [];
  for (const l of modelos) {
    const vs = series.map((s) => s.valor(l)).filter(Boolean).map((p) => p.v);
    if (vs.length > 1) conectores.push({ idx: l.idx, a: Math.min(...vs), b: Math.max(...vs) });
  }
  const filhos = [
    { type: 'link', data: conectores, encode: { x: ['a', 'b'], y: ['idx', 'idx'] }, style: { stroke: '#D5DBE5', lineWidth: 2 }, ...SEM },
    { type: 'text', data: modelos, encode: { x: () => x0, y: 'idx', text: 'nome' }, style: texto({ fontSize: 13, fontWeight: 600, fill: COR.tinta, textAlign: 'right', textBaseline: 'bottom', dx: -12, dy: 1 }), ...SEM },
    { type: 'text', data: modelos, encode: { x: () => x0, y: 'idx', text: 'detalhe' }, style: texto({ fontSize: 11.5, fill: COR.tinta3, textAlign: 'right', textBaseline: 'top', dx: -12, dy: 2 }), ...SEM },
    { type: 'text', data: linhas.filter((l) => l.cabecalho), encode: { x: () => x0, y: 'idx', text: 'nome' }, style: texto({ fontSize: 11, fontWeight: 700, fill: COR.tinta3, textAlign: 'left', textBaseline: 'middle', dx: -(op.esquerda ?? 150) + 4 }), ...SEM },
  ];
  for (const s of series) {
    const pontos = modelos.map((l) => ({ l, p: s.valor(l) })).filter((o) => o.p).map((o) => ({ idx: o.l.idx, v: o.p.v, dica: o.p.dica, nome: `${o.l.nome} · ${o.l.detalhe}` }));
    const apagado = destaque !== 'todas' && destaque !== s.cod;
    filhos.push({
      type: 'point', data: pontos,
      encode: { x: 'v', y: 'idx', shape: 'point', size: 6.5 },
      scale: { size: { type: 'identity' }, shape: { type: 'identity', independent: true } },
      style: { fill: s.cor, fillOpacity: apagado ? 0.12 : 1, stroke: '#FFFFFF', lineWidth: 1.5, strokeOpacity: apagado ? 0.2 : 1, transform: `translate(0, ${s.deslocamento ?? 0})` },
      animate: false,
      tooltip: { title: (d) => d.nome, items: [(d) => ({ name: s.rotulo, value: d.dica, color: s.cor })] },
    });
  }
  return {
    type: 'view',
    theme: 'classic',
    paddingLeft: op.esquerda ?? 150,
    paddingRight: 18,
    paddingTop: 6,
    paddingBottom: 26,
    scale: {
      x: op.log
        ? { type: 'log', base: 10, domain: [x0, x1], nice: false, tickMethod: () => ticks }
        : { type: 'linear', domain: [x0, x1], nice: false, tickMethod: () => ticks },
      y: { type: 'linear', domain: [n - 0.5, -0.5], nice: false },
    },
    axis: { x: eixoValor({ labelFormatter: formato }), y: false },
    legend: false,
    children: filhos,
  };
}

function pontos(el, linhas, series, op = {}) {
  const chart = preparar(el, linhas.length * (op.passo ?? 40) + 34);
  const estado = { ...op };
  chart.options(specPontos(linhas, series, estado));
  chart.render();
  return { chart, atualizar: (novo = {}) => { Object.assign(estado, novo); chart.options(specPontos(linhas, series, estado)); chart.render(); } };
}

// linhas de modelos agrupadas por família, com cabeçalho
function linhasModelos(posicoes, extra = () => ({})) {
  const linhas = [];
  const grupos = [['menores', 'MENORES E ABERTOS'], ['fronteira', 'FRONTEIRA']];
  for (const [familia, titulo] of grupos) {
    linhas.push({ idx: linhas.length, cabecalho: true, nome: titulo });
    for (const p of posicoes.filter((x) => x.familia === familia)) {
      linhas.push({ idx: linhas.length, nome: p.nome, detalhe: p.detalhe, p, ...extra(p) });
    }
  }
  return linhas;
}

// ---------- diferença pareada com intervalo ----------
function specFloresta(linhas, op) {
  const n = linhas.length;
  const estreito = op.largura < 560;
  const modelos = linhas.filter((l) => !l.cabecalho);
  const filhos = [
    { type: 'link', data: [{ a: 0, b: 0, y0: -0.5, y1: n - 0.5 }], encode: { x: ['a', 'b'], y: ['y0', 'y1'] }, style: { stroke: COR.tinta2, lineWidth: 1 }, ...SEM },
    { type: 'link', data: modelos, encode: { x: ['lo', 'hi'], y: ['idx', 'idx'] }, style: { stroke: (d) => (d.exclui ? COR.d : COR.ref), lineWidth: 3 }, ...SEM },
    {
      type: 'point', data: modelos, encode: { x: 'diff', y: 'idx', shape: 'point', size: 4.5 },
      scale: { size: { type: 'identity' }, shape: { type: 'identity', independent: true } },
      style: { fill: COR.tinta, fillOpacity: 1, stroke: '#FFFFFF', lineWidth: 1.2 }, animate: false,
      tooltip: { title: (d) => `${d.nomeCompleto} · ${d.rep}`, items: [(d) => ({ name: 'C2 − C1', value: `${dec(d.diff)} [${dec(d.lo)}; ${dec(d.hi)}] · ${d.n} pares` })] },
    },
    { type: 'text', data: modelos.filter((l) => l.rep === 'R1'), encode: { x: () => -1, y: 'idx', text: 'nome' }, style: texto({ fontSize: 12.5, fontWeight: 600, fill: COR.tinta, textAlign: 'right', textBaseline: 'middle', dx: -34, dy: 11 }), ...SEM },
    { type: 'text', data: modelos, encode: { x: () => -1, y: 'idx', text: 'rep' }, style: texto({ fontSize: 10.5, fill: COR.tinta3, textAlign: 'right', textBaseline: 'middle', dx: -8 }), ...SEM },
    { type: 'text', data: linhas.filter((l) => l.cabecalho), encode: { x: () => -1, y: 'idx', text: 'nome' }, style: texto({ fontSize: 11, fontWeight: 700, fill: COR.tinta3, textAlign: 'left', textBaseline: 'middle', dx: -186 }), ...SEM },
  ];
  if (!estreito) {
    filhos.push({ type: 'text', data: modelos, encode: { x: () => 1, y: 'idx', text: (d) => `${dec(d.diff)} [${dec(d.lo)}; ${dec(d.hi)}]` }, style: texto({ fontSize: 11, fill: COR.tinta2, textAlign: 'left', textBaseline: 'middle', dx: 10 }), ...SEM });
  }
  return {
    type: 'view',
    theme: 'classic',
    paddingLeft: 190,
    paddingRight: estreito ? 14 : 132,
    paddingTop: 6,
    paddingBottom: 26,
    scale: {
      x: { type: 'linear', domain: [-1, 1], nice: false, tickMethod: () => [-1, -0.5, 0, 0.5, 1] },
      y: { type: 'linear', domain: [n - 0.5, -0.5], nice: false },
    },
    axis: { x: eixoValor({ labelFormatter: (v) => dec(v, v % 1 === 0 ? 0 : 1) }), y: false },
    legend: false,
    children: filhos,
  };
}

function floresta(el, linhas) {
  const chart = preparar(el, linhas.length * 23 + 34);
  const montar = () => specFloresta(linhas, { largura: el.clientWidth });
  chart.options(montar());
  chart.render();
  return { chart, atualizar: () => { chart.options(montar()); chart.render(); } };
}

// ---------- mapa de calor dos casos ----------
function rampa(t) {
  const a = [0xF2, 0xF4, 0xF8];
  const b = [0x9E, 0x3B, 0x3B];
  const c = a.map((x, i) => Math.round(x + (b[i] - x) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

function calor(el, linhas) {
  // linhas: { rotulo, tipo, celulas: { C1: {e, n}, C2, D } }
  const colunas = ['tipo', 'C1', 'C2', 'D'];
  const nomesColunas = { tipo: 'tipo', C1: 'C1 interface', C2: 'C2 código', D: 'D combinação' };
  const dados = [];
  for (const l of linhas) {
    for (const c of ['C1', 'C2', 'D']) {
      const { e, n } = l.celulas[c];
      dados.push({ rotulo: l.rotulo, cond: c, e, n, taxa: n ? e / n : null, detalhe: l.detalhe });
    }
  }
  const chart = preparar(el, linhas.length * 34 + 40);
  chart.options({
    type: 'view',
    theme: 'classic',
    paddingLeft: 320,
    paddingRight: 8,
    paddingTop: 30,
    paddingBottom: 6,
    scale: {
      x: { type: 'band', domain: colunas, paddingInner: 0, paddingOuter: 0 },
      y: { type: 'band', domain: linhas.map((l) => l.rotulo), paddingInner: 0, paddingOuter: 0 },
    },
    axis: {
      x: { position: 'top', title: false, labelFormatter: (v) => nomesColunas[v], labelFontFamily: FONTE, labelFontSize: 12, labelFontWeight: 600, labelFill: COR.tinta, labelOpacity: 1, line: false, tick: false, grid: false },
      y: { title: false, labelFontFamily: FONTE, labelFontSize: 12, labelFill: COR.tinta, labelOpacity: 1, labelSpacing: 8, line: false, tick: false, grid: false },
    },
    legend: false,
    children: [
      {
        type: 'cell', data: linhas.map((l) => ({ rotulo: l.rotulo, cond: 'tipo', tipo: l.tipo })),
        encode: { x: 'cond', y: 'rotulo' }, style: { fill: '#FFFFFF', stroke: '#FFFFFF', lineWidth: 2 },
        labels: [{ text: 'tipo', position: 'inside', fontFamily: FONTE, fontSize: 11.5, fill: COR.tinta2, fillOpacity: 1 }],
        ...SEM,
      },
      {
        type: 'cell', data: dados, encode: { x: 'cond', y: 'rotulo' },
        style: { fill: (d) => (d.taxa == null ? '#FFFFFF' : rampa(d.taxa)), stroke: '#FFFFFF', lineWidth: 2, fillOpacity: 1 },
        labels: [{
          text: (d) => (d.n ? `${d.e}/${d.n}` : '—'), position: 'inside', fontFamily: '"IBM Plex Mono", Consolas, monospace', fontSize: 12,
          fill: (d) => (d.taxa != null && d.taxa > 0.45 ? '#FFFFFF' : COR.tinta), fillOpacity: 1,
        }],
        animate: false,
        tooltip: { title: (d) => d.rotulo, items: [(d) => ({ name: nomesColunas[d.cond], value: d.n ? `${d.e} erros em ${d.n} decisões (${pct(100 * d.taxa)})` : 'sem decisão binária' }), (d) => ({ name: 'caso', value: d.detalhe })] },
      },
    ],
  });
  chart.render();
  return { chart, atualizar: () => {} };
}


// ---------- cores de estado (painel 2) ----------
const EST = {
  acerto: '#2F7D6D', erro: '#9E3B3B', inconclusiva: '#C9A15B', semResposta: '#A9B1BE',
  acertoClaro: '#CFE3DD', erroClaro: '#EBCACA', erroMedio: '#D9877A',
};

// rótulos de modelo à esquerda, com cabeçalhos de família (eixo em bandas)
function rotulosBanda(linhas, esquerda) {
  const modelos = linhas.filter((l) => !l.cabecalho);
  return [
    { type: 'text', data: modelos, encode: { x: 'chave', y: () => 0, text: 'nome' }, style: texto({ fontSize: 14, fontWeight: 600, fill: COR.tinta, textAlign: 'right', textBaseline: 'bottom', dx: -10, dy: 1 }), ...SEM },
    { type: 'text', data: modelos, encode: { x: 'chave', y: () => 0, text: 'detalhe' }, style: texto({ fontSize: 13, fontWeight: (d) => P[d.p]?.nome.includes('Luna') ? 700 : 400, fill: (d) => P[d.p]?.nome.includes('Luna') ? COR.fronteira : COR.tinta3, textAlign: 'right', textBaseline: 'top', dx: -10, dy: 2 }), ...SEM },
    { type: 'text', data: linhas.filter((l) => l.cabecalho), encode: { x: 'chave', y: () => 0, text: 'nome' }, style: texto({ fontSize: 10.5, fontWeight: 700, fill: COR.tinta3, textAlign: 'left', textBaseline: 'middle', dx: -esquerda + 2 }), ...SEM },
  ];
}

// ---------- barras empilhadas por resultado ----------
// dados: { chave, nome, estado, n }; estados: { cod, rotulo, cor, claro }
function specPilhas(linhas, dados, estados, op) {
  const esquerda = op.rotulos ? 148 : 8;
  const porCod = Object.fromEntries(estados.map((e) => [e.cod, e]));
  const ordem = Object.fromEntries(estados.map((e, i) => [e.cod, i]));
  const visiveis = dados.filter((d) => d.n > 0).sort((a, b) => (a.chave === b.chave ? ordem[a.estado] - ordem[b.estado] : 0));
  return {
    type: 'view',
    theme: 'classic',
    coordinate: { transform: [{ type: 'transpose' }] },
    paddingLeft: esquerda,
    paddingRight: 10,
    paddingTop: 4,
    paddingBottom: 24,
    scale: {
      x: { type: 'band', domain: linhas.map((l) => l.chave), paddingInner: 0.28, paddingOuter: 0.1 },
      y: { type: 'linear', domain: [0, op.max], nice: false, tickMethod: () => op.ticks },
    },
    axis: { x: false, y: eixoValor({ labelFormatter: (v) => String(v) }) },
    legend: false,
    children: [
      { type: 'interval', data: linhas.filter((l) => !l.cabecalho), encode: { x: 'chave', y: () => op.max }, style: { fill: COR.trilho, fillOpacity: 1, maxWidth: 22 }, ...SEM },
      {
        type: 'interval', data: visiveis,
        encode: { x: 'chave', y: 'n', color: 'estado' },
        transform: [{ type: 'stackY' }],
        scale: { color: { domain: estados.map((e) => e.cod), range: estados.map((e) => e.cor) } },
        style: { maxWidth: 22, stroke: '#FFFFFF', lineWidth: 1, fillOpacity: 1 },
        labels: [{
          text: (d) => (d.n >= (op.minRotulo ?? 2) ? String(d.n) : ''), position: 'inside',
          fontFamily: FONTE, fontSize: 11, fontWeight: 600, fillOpacity: 1,
          fill: (d) => (porCod[d.estado].claro ? '#FFFFFF' : COR.tinta),
        }],
        animate: false,
        tooltip: { title: (d) => d.nome, items: [(d) => ({ name: porCod[d.estado].rotulo, value: `${d.n} de ${op.max}`, color: porCod[d.estado].cor })] },
      },
      ...(op.rotulos ? rotulosBanda(linhas, esquerda) : []),
    ],
  };
}

function pilhas(el, linhas, dados, estados, op) {
  const estado = { ...op };
  const primeiroDaLinha = () => {
    const painel = el.closest('.painel');
    const grupo = painel && painel.parentElement;
    if (!painel || !grupo) return true;
    const irmaos = [...grupo.children];
    const i = irmaos.indexOf(painel);
    return i <= 0 || Math.abs(irmaos[i - 1].offsetTop - painel.offsetTop) > 4;
  };
  const chart = preparar(el, linhas.length * (op.passo ?? 32) + 30);
  const montar = () => specPilhas(linhas, estado.dados ?? dados, estado.estados ?? estados, { ...estado, rotulos: op.sempreRotulos || primeiroDaLinha() });
  chart.options(montar());
  chart.render();
  return {
    chart,
    atualizar: (novo = {}) => {
      Object.assign(estado, novo);
      if (novo.linhas) { linhas = novo.linhas; el.style.height = `${linhas.length * (op.passo ?? 32) + 30}px`; }
      chart.options(montar());
      chart.render();
    },
  };
}

// ---------- barras divergentes: piorou × melhorou ----------
// dados: { chave, nome, piorou, melhorou, AA, EE, fora }
function specDivergente(linhas, dados, op) {
  const estreito = op.largura < 440;
  const esquerda = 128;
  const max = op.max;
  const barras = [];
  for (const d of dados) {
    if (d.piorou) barras.push({ chave: d.chave, nome: d.nome, lado: 'piorou', v: -d.piorou, n: d.piorou });
    if (d.melhorou) barras.push({ chave: d.chave, nome: d.nome, lado: 'melhorou', v: d.melhorou, n: d.melhorou });
  }
  const passo = Math.max(2, Math.ceil(max / 4 / 2) * 2);
  const ticks = [];
  for (let t = -max; t <= max; t += passo) ticks.push(t);
  const filhos = [
    {
      type: 'interval', data: barras, encode: { x: 'chave', y: 'v', color: 'lado' },
      scale: { color: { domain: ['piorou', 'melhorou'], range: [EST.erro, EST.acerto] } },
      style: { maxWidth: 18, fillOpacity: 1 }, animate: false,
      tooltip: { title: (d) => d.nome, items: [(d) => ({ name: d.lado === 'piorou' ? op.rotuloPiorou : op.rotuloMelhorou, value: String(d.n), color: d.lado === 'piorou' ? EST.erro : EST.acerto })] },
    },
    { type: 'text', data: barras.filter((b) => b.lado === 'piorou'), encode: { x: 'chave', y: 'v', text: 'n' }, style: texto({ fontSize: 11.5, fontWeight: 700, fill: EST.erro, textAlign: 'right', textBaseline: 'middle', dx: -5 }), ...SEM },
    { type: 'text', data: barras.filter((b) => b.lado === 'melhorou'), encode: { x: 'chave', y: 'v', text: 'n' }, style: texto({ fontSize: 11.5, fontWeight: 700, fill: EST.acerto, textAlign: 'left', textBaseline: 'middle', dx: 5 }), ...SEM },
    ...rotulosBanda(linhas, esquerda).map((m) => ({ ...m, encode: { ...m.encode, y: () => -max } })),
  ];
  if (!estreito) {
    filhos.push({ type: 'text', data: dados, encode: { x: 'chave', y: () => max, text: (d) => `iguais: ${d.AA} acertos` }, style: texto({ fontSize: 10.5, fill: COR.tinta2, textAlign: 'left', textBaseline: 'bottom', dx: 10, dy: 1 }), ...SEM });
    filhos.push({ type: 'text', data: dados, encode: { x: 'chave', y: () => max, text: (d) => `${d.EE} erros${d.fora ? ` · fora ${d.fora}` : ''}` }, style: texto({ fontSize: 10.5, fill: COR.tinta3, textAlign: 'left', textBaseline: 'top', dx: 10, dy: 2 }), ...SEM });
  }
  return {
    type: 'view',
    theme: 'classic',
    coordinate: { transform: [{ type: 'transpose' }] },
    paddingLeft: esquerda,
    paddingRight: estreito ? 14 : 124,
    paddingTop: 4,
    paddingBottom: 24,
    scale: {
      x: { type: 'band', domain: linhas.map((l) => l.chave), paddingInner: 0.3, paddingOuter: 0.1 },
      y: { type: 'linear', domain: [-max, max], nice: false, tickMethod: () => ticks },
    },
    axis: { x: false, y: eixoValor({ labelFormatter: (v) => String(Math.abs(v)), gridStroke: COR.grade }) },
    legend: false,
    children: filhos,
  };
}

function divergente(el, linhas, dados, op) {
  const estado = { ...op, dados };
  const chart = preparar(el, linhas.length * 32 + 30);
  const montar = () => specDivergente(linhas, estado.dados, { ...estado, largura: el.clientWidth });
  chart.options(montar());
  chart.render();
  return { chart, atualizar: (novo = {}) => { Object.assign(estado, novo); chart.options(montar()); chart.render(); } };
}

// ---------- dados ----------
const P = DADOS.posicoes;
const CASOS = DADOS.casos;
const CUSTOS = DADOS.custos;
const U = new Map();
for (const [p, c, cond, rep, est, just] of DADOS.unidades) U.set(`${p}|${c}|${cond}|${rep}`, { est, just });
const un = (p, c, cond, rep) => U.get(`${p}|${c}|${cond}|${rep}`);
const ehBin = (e) => ['VP', 'VN', 'FP', 'FN'].includes(e);
const ehAcerto = (e) => e === 'VP' || e === 'VN';
const grupoDe = (cls) => cls[0] === 'P' ? 'P' : cls[0] === 'B' ? 'B' : 'S';
const NOMES_COND = { C1: 'interface', C2: 'código', D: 'combinação' };
const ACENTOS = [
  ['proprietario', 'proprietário'], ['padrao', 'padrão'], ['comparacao', 'comparação'], ['prontidao', 'prontidão'],
  ['realizacao', 'realização'], ['acao', 'ação'], ['selecao', 'seleção'], ['deterministico', 'determinístico'],
  ['nao ', 'não '], ['mudancas', 'mudanças'], ['memoria', 'memória'], ['copia', 'cópia'], ['sintetico', 'sintético'],
];
const acentuar = (s) => ACENTOS.reduce((t, [a, b]) => t.replaceAll(a, b), s || '');
const nomePosicao = (p) => p.nome + (p.detalhe ? ` · ${p.detalhe}` : '');
const nomeModelo = (p) => nomePosicao(P[p]);
const virgula = (v, casas = 1) => v.toFixed(casas).replace('.', ',');
const FALHAS = {
  recusa_filtro_provedor: 'recusa do filtro de segurança do provedor',
  truncado_max_tokens_raciocinio: 'limite de tokens gasto no raciocínio',
  erro_api_resposta_truncada: 'erro da API com resposta cortada',
  falha_transporte_terminal: 'falha de transporte',
  json_invalido: 'resposta fora do formato',
};

function el(tag, attrs = {}, filhos = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'texto') n.textContent = v;
    else n.setAttribute(k, v);
  }
  for (const f of [].concat(filhos)) if (f != null && f !== false) n.append(f);
  return n;
}

function rotuloModelo(p) {
  const filhos = [el('b', { texto: p.nome })];
  if (p.detalhe) filhos.push(el('br'), el(p.nome.includes('Luna') ? 'span' : 'small', { class: p.nome.includes('Luna') ? 'selo-luna' : '', texto: p.detalhe }));
  return filhos;
}

function linhasBanda() {
  const linhas = [];
  for (const [familia, titulo] of [['menores', 'MENORES E ABERTOS'], ['fronteira', 'FRONTEIRA']]) {
    linhas.push({ chave: `h-${familia}`, cabecalho: true, nome: titulo });
    P.forEach((p, i) => { if (p.familia === familia) linhas.push({ chave: `m${i}`, p: i, nome: p.nome, detalhe: p.detalhe }); });
  }
  return linhas;
}
const LINHAS = linhasBanda();

// ---------- resultados por modelo ----------
function estadosResultado(grupo) {
  const perigo = grupo === 'P';
  return [
    { cod: 'acerto', rotulo: perigo ? 'bloqueou (acerto)' : 'permitiu (acerto)', cor: EST.acerto, claro: true },
    { cod: 'erro', rotulo: perigo ? 'permitiu (erro)' : 'bloqueou (erro)', cor: EST.erro, claro: true },
    { cod: 'INC', rotulo: 'inconclusiva', cor: EST.inconclusiva, claro: false },
    { cod: 'F', rotulo: 'sem resposta', cor: EST.semResposta, claro: false },
  ];
}
const ESTADOS_MISTOS = [
  { cod: 'acerto', rotulo: 'acerto', cor: EST.acerto, claro: true },
  { cod: 'erro', rotulo: 'erro', cor: EST.erro, claro: true },
  { cod: 'INC', rotulo: 'inconclusiva', cor: EST.inconclusiva, claro: false },
  { cod: 'F', rotulo: 'sem resposta', cor: EST.semResposta, claro: false },
];

function contar(arm, cond, filtroCaso) {
  const casos = CASOS.map((c, i) => ({ ...c, i })).filter((c) => c.arm === arm && filtroCaso(c));
  const dados = [];
  for (const l of LINHAS.filter((x) => !x.cabecalho)) {
    const cont = { acerto: 0, erro: 0, INC: 0, F: 0 };
    for (const c of casos) {
      for (const rep of ['R1', 'R2']) {
        const e = un(l.p, c.i, cond, rep).est;
        if (ehBin(e)) cont[ehAcerto(e) ? 'acerto' : 'erro'] += 1;
        else if (e === 'INC') cont.INC += 1;
        else cont.F += 1;
      }
    }
    for (const [estado, n] of Object.entries(cont)) dados.push({ chave: l.chave, nome: nomeModelo(l.p), estado, n });
  }
  return { dados, max: casos.length * 2 };
}

const ticksAte = (max) => {
  const passo = max <= 12 ? 3 : max <= 24 ? 6 : Math.ceil(max / 4);
  const t = [];
  for (let v = 0; v <= max; v += passo) t.push(v);
  return t;
};

function legendaEstados(id, estados) {
  document.getElementById(id).replaceChildren(...estados.map((e) => el('span', {}, [el('i', { class: 'amostra', style: `background:${e.cor}` }), e.rotulo])));
}

let grupoNint = 'P';
const graficos = {};

function desenharNint() {
  const estados = estadosResultado(grupoNint);
  legendaEstados('legenda-nint', estados);
  for (const cond of ['C1', 'C2', 'D']) {
    const { dados, max } = contar('N-INT', cond, (c) => grupoDe(c.cls) === grupoNint);
    const id = `g-nint-${cond}`;
    if (graficos[id]) graficos[id].atualizar({ dados, estados, max, ticks: ticksAte(max) });
    else graficos[id] = pilhas(document.getElementById(id), LINHAS, dados, estados, { max, ticks: ticksAte(max) });
  }
}

function desenharExterno(prefixo, arm, cond, paineis) {
  legendaEstados(`legenda-${arm === 'Connor' ? 'connor' : 'mcptox'}`, ESTADOS_MISTOS);
  for (const [sufixo, filtro] of paineis) {
    const { dados, max } = contar(arm, cond, filtro);
    const id = `g-${prefixo}-${sufixo}`;
    graficos[id] = pilhas(document.getElementById(id), LINHAS, dados, ESTADOS_MISTOS, { max, ticks: ticksAte(max), passo: 30 });
  }
}

// ---------- mudanças nos mesmos casos ----------
const CAT_T = {
  EA: { rotulo: 'erro → acerto', cor: EST.acerto },
  AE: { rotulo: 'acerto → erro', cor: EST.erro },
  AA: { rotulo: 'acerto nos dois', cor: EST.acertoClaro },
  EE: { rotulo: 'erro nos dois', cor: EST.erroClaro },
  fora: { rotulo: 'fora do par (inconclusiva ou sem resposta)', cor: null },
};
function transicao(p, c, a, b, rep) {
  const ea = un(p, c, a, rep).est;
  const eb = un(p, c, b, rep).est;
  if (!ehBin(ea) || !ehBin(eb)) return 'fora';
  return (ehAcerto(ea) ? 'A' : 'E') + (ehAcerto(eb) ? 'A' : 'E');
}
const casosNint = (grupo) => CASOS.map((c, i) => ({ ...c, i })).filter((c) => c.arm === 'N-INT' && grupoDe(c.cls) === grupo);

function resumoTransicoes(a, b, grupo) {
  return LINHAS.filter((l) => !l.cabecalho).map((l) => {
    const n = { EA: 0, AE: 0, AA: 0, EE: 0, fora: 0 };
    for (const c of casosNint(grupo)) for (const rep of ['R1', 'R2']) n[transicao(l.p, c.i, a, b, rep)] += 1;
    return { chave: l.chave, nome: nomeModelo(l.p), piorou: n.AE, melhorou: n.EA, AA: n.AA, EE: n.EE, fora: n.fora };
  });
}
const maxPar = (...listas) => {
  const m = Math.max(...listas.flat().map((d) => Math.max(d.piorou, d.melhorou)), 2);
  return Math.ceil(m / 4) * 4;
};

const CAT_D = {
  melhora: { rotulo: 'D corrige um erro de C1 ou C2', cor: '#2F7D6D' },
  piora: { rotulo: 'D desfaz um acerto de C1 ou C2', cor: '#9E3B3B' },
  igual: { rotulo: 'mesmo resultado nas três', cor: '#C6CEDA' },
  fora: { rotulo: 'sem comparação (dúvida ou falha)', cor: null },
};
function categoriaD(p, c, rep) {
  const e1 = un(p, c, 'C1', rep).est;
  const e2 = un(p, c, 'C2', rep).est;
  const ed = un(p, c, 'D', rep).est;
  if (![e1, e2, ed].every(ehBin)) return 'fora';
  const acertos = ehAcerto(e1) + ehAcerto(e2);
  if (ehAcerto(ed)) return acertos === 2 ? 'igual' : 'melhora';
  return acertos === 0 ? 'igual' : 'piora';
}

function chaveCores(id, cats) {
  document.getElementById(id).replaceChildren(...Object.values(cats).map((c) => el('span', {}, [el('i', { class: `amostra${c.cor ? '' : ' vazio'}`, style: c.cor ? `background:${c.cor}` : '' }), c.rotulo])));
}

function ordenarCasos(casos) {
  const ordemVis = { reveladora: 0, nao_reveladora: 1 };
  return casos.sort((a, b) => (a.cls.localeCompare(b.cls)) || ((ordemVis[a.vis] ?? 2) - (ordemVis[b.vis] ?? 2)) || acentuar(a.cap).localeCompare(acentuar(b.cap)));
}
const rotuloTipo = (c) => {
  const classe = { P: 'perigoso', B: 'legítimo', S: 'sem mudança' }[c.cls];
  const vis = c.vis === 'reveladora' ? ' · descrição revela' : c.vis === 'nao_reveladora' ? ' · descrição esconde' : '';
  return `${classe}${vis}`;
};

function montarGrade(idTabela, idDetalhe, grupo, categoria, cats, condsDetalhe) {
  const tabela = document.getElementById(idTabela);
  const cab = el('tr', {}, [el('th', { class: 'caso', texto: 'caso' }), ...P.map((p) => el('th', {}, rotuloModelo(p)))]);
  const corpo = el('tbody');
  let classeAtual = null;
  for (const c of ordenarCasos(casosNint(grupo))) {
    if (c.cls !== classeAtual) {
      classeAtual = c.cls;
      corpo.append(el('tr', { class: 'separador' }, el('td', { colspan: String(P.length + 1), texto: { P: 'casos perigosos', B: 'atualizações legítimas' }[c.cls] })));
    }
    const linha = el('tr', {}, el('td', { class: 'caso' }, [acentuar(c.cap), el('small', { texto: c.vis === 'reveladora' ? 'descrição revela' : c.vis === 'nao_reveladora' ? 'descrição esconde' : c.id })]));
    P.forEach((p, pi) => {
      const quadros = ['R1', 'R2'].map((rep) => {
        const k = categoria(pi, c.i, rep);
        return el('i', { class: cats[k].cor ? '' : 'vazio', style: cats[k].cor ? `background:${cats[k].cor}` : '', title: `${rep}: ${cats[k].rotulo}` });
      });
      const botao = el('button', { type: 'button', class: 'celula', 'aria-pressed': 'false', 'aria-label': `${acentuar(c.cap)}, ${nomeModelo(pi)}` }, quadros);
      botao.addEventListener('click', () => {
        tabela.querySelectorAll('.celula').forEach((b) => b.setAttribute('aria-pressed', String(b === botao)));
        mostrarDetalheCaso(idDetalhe, pi, c, condsDetalhe);
      });
      linha.append(el('td', {}, botao));
    });
    corpo.append(linha);
  }
  tabela.replaceChildren(el('thead', {}, cab), corpo);
  document.getElementById(idDetalhe).hidden = true;
}

function chipAcao(est) {
  if (est === 'INC') return el('span', { class: 'acao inc', texto: 'inconclusiva' });
  if (est.startsWith('F:')) return el('span', { class: 'acao falha', texto: 'sem resposta' });
  const acao = est === 'VP' || est === 'FP' ? 'bloqueou' : 'permitiu';
  return el('span', { class: `acao ${ehAcerto(est) ? 'ok' : 'erro'}`, texto: `${acao} · ${ehAcerto(est) ? 'acerto' : 'erro'}` });
}
function textoJust(u) {
  if (u.est.startsWith('F:')) return FALHAS[u.est.slice(2)] || u.est.slice(2);
  return u.just ? `“${u.just}”` : 'sem justificativa no texto da resposta';
}
function linhaCond(cond, u) {
  const cor = { C1: 'var(--c1)', C2: 'var(--c2)', D: 'var(--d)' }[cond];
  return el('div', { class: 'linha-cond' }, [el('span', { class: 'cod', style: `background:${cor}`, texto: cond }), el('p', {}, [chipAcao(u.est), textoJust(u)])]);
}

function mostrarDetalheCaso(idDetalhe, p, c, conds) {
  const alvo = document.getElementById(idDetalhe);
  alvo.replaceChildren(
    el('h6', { texto: `${acentuar(c.cap)} · ${nomeModelo(p)}` }),
    el('span', { class: 'meta', texto: `${c.id} · ${rotuloTipo(c)} · gabarito: ${c.gt}` }),
    el('div', { class: 'reps' }, ['R1', 'R2'].map((rep) => el('div', { class: 'rep' }, [el('b', { texto: rep }), ...conds.map((cond) => linhaCond(cond, un(p, c.i, cond, rep)))]))),
  );
  alvo.hidden = false;
}

// ---------- consistência ----------
const COLUNAS_CONSIST = [['N-INT', 'C1'], ['N-INT', 'C2'], ['N-INT', 'D'], ['MCPTox', 'C1'], ['Connor', 'C2']];
function paresConsist(p, colunas) {
  let ambos = 0, iguais = 0, r3 = 0;
  const trocas = [];
  for (const [arm, cond] of colunas) {
    CASOS.forEach((c, i) => {
      if (c.arm !== arm) return;
      const u1 = un(p, i, cond, 'R1');
      const u2 = un(p, i, cond, 'R2');
      if (un(p, i, cond, 'R3')) r3 += 1;
      if (u1.est.startsWith('F:') || u2.est.startsWith('F:')) return;
      ambos += 1;
      const a1 = acaoDe(u1.est);
      const a2 = acaoDe(u2.est);
      if (a1 === a2) iguais += 1;
      else trocas.push({ c: { ...c, i }, cond, arm });
    });
  }
  return { ambos, iguais, r3, trocas };
}
const acaoDe = (e) => (e === 'INC' ? 'inconclusiva' : e === 'VP' || e === 'FP' ? 'bloquear' : 'permitir');

function corConsist(trocas) {
  if (!trocas) return '#EEF2F6';
  const t = Math.min(trocas / 5, 1);
  const a = [0xF4, 0xE7, 0xCC];
  const b = [0xC9, 0xA1, 0x5B];
  return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * t)).join(',')})`;
}

function montarConsistencia() {
  const tabela = document.getElementById('tb-consist');
  const r3 = DADOS.unidades.filter((u) => u[3] === 'R3');
  const resultadoR3 = (unidades) => [
    unidades.filter((u) => ehAcerto(u[4])).length,
    unidades.filter((u) => ehBin(u[4]) && !ehAcerto(u[4])).length,
    unidades.filter((u) => u[4] === 'INC').length,
  ];
  const cab = el('tr', {}, [el('th', { texto: '' }), ...COLUNAS_CONSIST.map(([arm, cond]) => el('th', { texto: `${arm} · ${cond}` })), el('th', { class: 'cab-r3' }, [el('b', { texto: 'R3 por modelo' }), el('small', { texto: 'acertos / erros / inconclusivas' })])]);
  const corpo = el('tbody');
  const botoes = [];
  for (const [familia, titulo] of [['menores', 'Menores e abertos'], ['fronteira', 'Fronteira']]) {
    corpo.append(el('tr', {}, el('td', { colspan: String(COLUNAS_CONSIST.length + 2), style: 'padding-top:0.5rem;font-family:var(--cond);font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:#6B7383', texto: titulo })));
    P.forEach((pos, p) => {
      if (pos.familia !== familia) return;
      const linha = el('tr', {}, el('td', { class: 'modelo' }, rotuloModelo(pos)));
      for (const colunas of COLUNAS_CONSIST.map((x) => [x])) {
        const r = paresConsist(p, colunas);
        const trocas = r.trocas.length;
        const botao = el('button', { type: 'button', class: 'celula-c', 'aria-pressed': 'false', style: `background:${corConsist(trocas)}` }, [
          el('b', { texto: `${r.iguais}/${r.ambos}` }),
          el('small', { texto: `${trocas} ${trocas === 1 ? 'troca' : 'trocas'}` }),
        ]);
        botao.addEventListener('click', () => {
          botoes.forEach((b) => b.setAttribute('aria-pressed', String(b === botao)));
          mostrarTrocas(p, colunas, r);
        });
        botoes.push(botao);
        linha.append(el('td', {}, botao));
      }
      const unidadesR3 = r3.filter((u) => u[0] === p);
      const [acertos, erros, inc] = resultadoR3(unidadesR3);
      linha.append(el('td', { class: 'resultado-r3', 'aria-label': unidadesR3.length ? `${nomeModelo(p)}: ${acertos} acertos, ${erros} erros, ${inc} inconclusivas em R3` : `${nomeModelo(p)}: R3 não foi necessária` }, unidadesR3.length
        ? el('b', { texto: `${acertos} / ${erros} / ${inc}` })
        : el('small', { texto: 'não foi necessária' })));
      corpo.append(linha);
    });
  }
  tabela.replaceChildren(el('thead', {}, cab), corpo);
  const [acertos, erros, inc] = resultadoR3(r3);
  document.getElementById('resumo-r3').replaceChildren(`R3 nos ${r3.length} pares que divergiram, somando os modelos: `, el('b', { texto: `${acertos} acertos` }), ' · ', el('b', { texto: `${erros} erros` }), ' · ', el('b', { texto: `${inc} inconclusivas` }), '. A última coluna mostra o resultado de cada modelo.');
}

function mostrarTrocas(p, colunas, r) {
  const alvo = document.getElementById('detalhe-consist');
  const titulo = colunas.length === 1 ? `${colunas[0][0]} · ${colunas[0][1]}` : 'todos os conjuntos';
  const itens = r.trocas.length
    ? r.trocas.map(({ c, cond }) => el('div', { class: 'rep' }, [
      el('b', { texto: `${acentuar(c.cap)} · ${c.arm} · ${cond}` }),
      el('span', { class: 'meta', texto: `${c.id} · ${rotuloTipo(c)} · gabarito: ${c.gt}` }),
      ...['R1', 'R2', 'R3'].filter((rep) => un(p, c.i, cond, rep)).map((rep) => el('div', { class: 'linha-cond' }, [el('span', { class: 'cod', style: 'background:var(--tinta-2)', texto: rep }), el('p', {}, [chipAcao(un(p, c.i, cond, rep).est), textoJust(un(p, c.i, cond, rep))])])),
    ]))
    : [el('p', { texto: 'Nenhuma troca: as duas repetições deram a mesma ação em todos os pares com resposta.' })];
  alvo.replaceChildren(el('h6', { texto: `${nomeModelo(p)} · ${titulo}` }), el('div', { class: 'reps' }, itens));
  alvo.hidden = false;
}

// ---------- custo e latência ----------
const custo = (chave) => CUSTOS[chave];
const por1000 = (k) => (k && k.unidades ? (1000 * k.custo) / k.unidades : 0);
let escopoCamada = 'N-INT';
let escopoCm = 'N-INT';

function desenharCustoModelo() {
  const linhasCusto = P.map((pos, p) => {
    const k = custo(`${pos.id}|*|*`);
    const local = pos.id.startsWith('local-');
    const v = por1000(k);
    return { chave: `m${p}`, codigo: pos.nome, nome: pos.detalhe, valor: v, cor: pos.familia === 'fronteira' ? COR.fronteira : COR.menores, rotulo: local ? 'local' : `US$ ${virgula(v, 2)}`, fracao: local ? 'sem cobrança' : `total US$ ${virgula(k.custo, 2)}` };
  });
  graficos['g-custo-mod'] = barras(document.getElementById('g-custo-mod'), linhasCusto, { max: 15, ticks: [0, 5, 10, 15], formato: (v) => `${v}`, esquerda: 152, direita: 118, passo: 46, nomeValor: 'por 1.000 decisões' });
  const linhasLat = P.map((pos, p) => {
    const k = custo(`${pos.id}|*|*`);
    const med = k.lat_mediana / 1000;
    const p95 = k.lat_p95 / 1000;
    return { chave: `m${p}`, codigo: pos.nome, nome: pos.detalhe, valor: med, min: med, max: p95, cor: pos.familia === 'fronteira' ? COR.fronteira : COR.menores, rotulo: `${virgula(med)} s`, fracao: `p95 ${virgula(p95)} s` };
  });
  graficos['g-lat-mod'] = barras(document.getElementById('g-lat-mod'), linhasLat, { max: 20, ticks: [0, 5, 10, 15, 20], formato: (v) => `${v} s`, esquerda: 152, direita: 104, passo: 46, nomeValor: 'mediana' });

  const cab = ['Modelo', 'Decisões', 'Tentativas', 'Custo total', 'Por 1.000', 'Latência mediana', 'p95', 'Tokens de entrada', 'Tokens de saída'];
  const corpo = P.map((pos) => {
    const k = custo(`${pos.id}|*|*`);
    const local = pos.id.startsWith('local-');
    return el('tr', {}, [
      el('td', {}, rotuloModelo(pos)), el('td', { class: 'n', texto: String(k.unidades) }), el('td', { class: 'n', texto: String(k.tentativas) }),
      el('td', { class: 'n', texto: local ? 'local' : `US$ ${virgula(k.custo, 3)}` }), el('td', { class: 'n', texto: local ? '—' : `US$ ${virgula(por1000(k), 2)}` }),
      el('td', { class: 'n', texto: `${virgula(k.lat_mediana / 1000)} s` }), el('td', { class: 'n', texto: `${virgula(k.lat_p95 / 1000)} s` }),
      el('td', { class: 'n', texto: k.tok_entrada ? k.tok_entrada.toLocaleString('pt-BR') : '—' }), el('td', { class: 'n', texto: k.tok_saida ? (k.tok_saida ?? 0).toLocaleString('pt-BR') : '—' }),
    ]);
  });
  document.getElementById('tb-custo-mod').replaceChildren(el('thead', {}, el('tr', {}, cab.map((c, i) => el('th', { class: i ? 'n' : '', texto: c })))), el('tbody', {}, corpo));
}

function desenharCustoCamada() {
  const conds = ['C1', 'C2', 'D'];
  const linha = (c, valor, rotulo, fracao) => ({ chave: c, codigo: c, nome: NOMES_COND[c], valor, rotulo, fracao, cor: COR_COND[c] });
  const custoLinhas = conds.map((c) => { const k = custo(`nuvem|${escopoCamada}|${c}`); const v = por1000(k); return linha(c, v, `US$ ${virgula(v, 2)}`, `${k.unidades} decisões · US$ ${virgula(k.custo, 2)}`); });
  const tokLinhas = conds.map((c) => { const k = custo(`todos|${escopoCamada}|${c}`); return linha(c, k.tok_entrada, k.tok_entrada.toLocaleString('pt-BR'), `saída: ${(k.tok_saida ?? 0).toLocaleString('pt-BR')}`); });
  const latLinhas = conds.map((c) => { const k = custo(`nuvem|${escopoCamada}|${c}`); return linha(c, k.lat_mediana / 1000, `${virgula(k.lat_mediana / 1000)} s`, `p95 ${virgula(k.lat_p95 / 1000)} s`); });
  const specs = [
    ['g-camada-custo', custoLinhas, { max: 5, ticks: [0, 1, 2, 3, 4, 5], formato: (v) => `${v}`, nomeValor: 'por 1.000 decisões' }],
    ['g-camada-tok', tokLinhas, { max: 2000, ticks: [0, 500, 1000, 1500, 2000], formato: (v) => `${v}`, nomeValor: 'tokens de entrada' }],
    ['g-camada-lat', latLinhas, { max: 3, ticks: [0, 1, 2, 3], formato: (v) => `${v} s`, nomeValor: 'mediana' }],
  ];
  for (const [id, linhas, op] of specs) {
    graficos[id] = barras(document.getElementById(id), linhas, { ...op, esquerda: 96, direita: 130, passo: 58 });
  }
  const loc = conds.map((c) => `${virgula(custo(`local|${escopoCamada}|${c}`).lat_mediana / 1000)} s (${c})`);
  document.getElementById('nota-camada-local').textContent = `Nos dois modelos locais, sem cobrança, a latência mediana foi de ${loc.join(', ')}.`;
}

function desenharCustoCamadaModelo() {
  const linhas = LINHAS.map((l, idx) => ({ ...l, idx }));
  const serie = (c, valor, dica) => ({
    cod: c, cor: COR_COND[c], rotulo: `${c} ${NOMES_COND[c]}`, deslocamento: { C1: -7, C2: 0, D: 7 }[c],
    valor: (l) => { const k = custo(`${P[l.p].id}|${escopoCm}|${c}`); const v = k && valor(k, P[l.p]); return v == null ? null : { v, dica: dica(k, v) }; },
  });
  const conds = ['C1', 'C2', 'D'];
  const linhasP = linhas.map((l) => (l.cabecalho ? l : { ...l }));
  graficos['g-cm-custo'] = pontos(document.getElementById('g-cm-custo'), linhasP, conds.map((c) => serie(c, (k, pos) => (pos.id.startsWith('local-') ? null : por1000(k)), (k, v) => `US$ ${virgula(v, 2)} por 1.000 · ${k.unidades} decisões`)), { dominio: [0.05, 50], ticks: [0.1, 1, 10], log: true, formato: (v) => `US$ ${String(v).replace('.', ',')}`, esquerda: 128, passo: 36 });
  graficos['g-cm-lat'] = pontos(document.getElementById('g-cm-lat'), linhasP, conds.map((c) => serie(c, (k) => k.lat_mediana / 1000, (k, v) => `mediana ${virgula(v)} s · p95 ${virgula(k.lat_p95 / 1000)} s`)), { dominio: [0, 16], ticks: [0, 4, 8, 12, 16], formato: (v) => `${v} s`, esquerda: 128, passo: 36 });
  graficos['g-cm-tok'] = pontos(document.getElementById('g-cm-tok'), linhasP, conds.map((c) => serie(c, (k) => k.tok_entrada, (k, v) => `${v.toLocaleString('pt-BR')} de entrada · ${(k.tok_saida ?? 0).toLocaleString('pt-BR')} de saída`)), { dominio: [0, 3500], ticks: [0, 1000, 2000, 3000], formato: (v) => `${v}`, esquerda: 128, passo: 36 });

  const nuvem = P.filter((p) => !p.id.startsWith('local-'));
  const valores = nuvem.map((p) => conds.map((c) => por1000(custo(`${p.id}|${escopoCm}|${c}`))));
  const fora = nuvem.filter((p, i) => !(valores[i][0] < valores[i][1] && valores[i][1] < valores[i][2]));
  const todos = valores.flat();
  const faixa = `de US$ ${virgula(Math.min(...todos), 2)} a US$ ${virgula(Math.max(...todos), 2)} por 1.000 decisões`;
  const resp = document.getElementById('resposta-cm');
  resp.replaceChildren();
  if (!fora.length) {
    resp.append('Sim: nos seis modelos de nuvem, ', el('b', { texto: 'C1 é a defesa mais barata e D a mais cara' }), `. O que muda de um modelo para outro é a escala, ${faixa}.`);
  } else {
    resp.append(`A ordem C1 < C2 < D vale para ${nuvem.length - fora.length} dos ${nuvem.length} modelos de nuvem; a exceção é ${fora.map(nomePosicao).join(', ')}. A escala vai ${faixa}.`);
  }
}

// ---------- erros e justificativas ----------
const TIPOS = [
  { cod: 'FN', rotulo: 'perigo liberado', cor: EST.erro, claro: true },
  { cod: 'FP', rotulo: 'legítima bloqueada', cor: EST.erroMedio, claro: false },
  { cod: 'INC', rotulo: 'inconclusiva', cor: EST.inconclusiva, claro: false },
  { cod: 'F', rotulo: 'sem resposta', cor: EST.semResposta, claro: false },
];
const ERROS = [];
for (const [p, c, cond, rep, est, just] of DADOS.unidades) {
  if (rep === 'R3') continue;
  const tipo = est.startsWith('F:') ? 'F' : ['FN', 'FP', 'INC'].includes(est) ? est : null;
  if (!tipo) continue;
  const caso = CASOS[c];
  ERROS.push({ p, c, cond, rep, est, tipo, just, caso, busca: normalizar(`${acentuar(caso.cap)} ${caso.id} ${just} ${FALHAS[est.slice(2)] || ''}`) });
}
function normalizar(s) { return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
let limiteErros = 24;

function filtrarErros(ignorarModelo = false) {
  const modelo = document.getElementById('f-modelo').value;
  const conjunto = document.getElementById('f-conjunto').value;
  const defesa = document.getElementById('f-defesa').value;
  const tipo = document.getElementById('f-tipo').value;
  const busca = normalizar(document.getElementById('f-busca').value.trim());
  return ERROS.filter((e) => (ignorarModelo || !modelo || String(e.p) === modelo) && (!conjunto || e.caso.arm === conjunto) && (!defesa || e.cond === defesa) && (!tipo || e.tipo === tipo) && (!busca || e.busca.includes(busca)));
}

function desenharErros() {
  const base = filtrarErros(true);
  const dados = [];
  let maior = 0;
  for (const l of LINHAS.filter((x) => !x.cabecalho)) {
    const cont = Object.fromEntries(TIPOS.map((t) => [t.cod, 0]));
    base.filter((e) => e.p === l.p).forEach((e) => { cont[e.tipo] += 1; });
    maior = Math.max(maior, Object.values(cont).reduce((a, b) => a + b, 0));
    for (const t of TIPOS) dados.push({ chave: l.chave, nome: nomeModelo(l.p), estado: t.cod, n: cont[t.cod] });
  }
  const max = Math.max(10, Math.ceil(maior / 10) * 10);
  const ticks = [];
  for (let v = 0; v <= max; v += max / 5) ticks.push(v);
  if (graficos['g-erros']) graficos['g-erros'].atualizar({ dados, max, ticks });
  else graficos['g-erros'] = pilhas(document.getElementById('g-erros'), LINHAS, dados, TIPOS, { max, ticks, sempreRotulos: true, passo: 30, minRotulo: 3 });
  listarErros();
}

function listarErros() {
  const lista = filtrarErros();
  const ordemArm = { 'N-INT': 0, MCPTox: 1, Connor: 2 };
  lista.sort((a, b) => a.p - b.p || ordemArm[a.caso.arm] - ordemArm[b.caso.arm] || acentuar(a.caso.cap).localeCompare(acentuar(b.caso.cap)) || a.cond.localeCompare(b.cond) || a.rep.localeCompare(b.rep));
  const tipoPor = Object.fromEntries(TIPOS.map((t) => [t.cod, t]));
  const cards = lista.slice(0, limiteErros).map((e) => el('figure', { class: 'erro-card' }, [
    el('div', { class: 'rotulos' }, [
      el('span', { class: 'etiqueta', texto: nomeModelo(e.p) }),
      el('span', { class: 'etiqueta', texto: `${e.caso.arm} · ${e.cond} · ${e.rep}` }),
      el('span', { class: `acao ${e.tipo === 'INC' ? 'inc' : e.tipo === 'F' ? 'falha' : 'erro'}`, texto: tipoPor[e.tipo].rotulo }),
    ]),
    el('div', { class: 'cap' }, [acentuar(e.caso.cap), el('small', { texto: `${e.caso.id} · ${rotuloTipo(e.caso)}` })]),
    e.tipo === 'F' ? el('p', { class: 'sem', texto: `Sem resposta: ${FALHAS[e.est.slice(2)] || e.est.slice(2)}.` }) : el('blockquote', { texto: e.just ? `“${e.just}”` : 'sem justificativa no texto da resposta' }),
  ]));
  document.getElementById('lista-erros').replaceChildren(...cards);
  document.getElementById('contagem-erros').textContent = `${lista.length} ${lista.length === 1 ? 'decisão encontrada' : 'decisões encontradas'}${lista.length > limiteErros ? ` · mostrando ${limiteErros}` : ''}`;
  document.getElementById('mais-erros').hidden = lista.length <= limiteErros;
}

function montarFiltros() {
  const sel = document.getElementById('f-modelo');
  sel.append(el('option', { value: '', texto: 'todos' }), ...P.map((p, i) => el('option', { value: String(i), texto: nomePosicao(p) })));
  legendaEstados('legenda-erros', TIPOS);
  const aoMudar = () => { limiteErros = 24; desenharErros(); };
  ['f-modelo', 'f-conjunto', 'f-defesa', 'f-tipo'].forEach((id) => document.getElementById(id).addEventListener('change', aoMudar));
  let espera = null;
  document.getElementById('f-busca').addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(aoMudar, 200); });
  document.getElementById('mais-erros').addEventListener('click', () => { limiteErros += 24; listarErros(); });
}

// ---------- desenho ----------
const CLASSES = [
  ['P', 'perigosos', COR.perigo], ['B', 'legítimos', COR.legit], ['S', 'sem mudança', '#FFFFFF'],
];
function montarConjuntos() {
  const info = {
    'N-INT': ['Núcleo de comparação', 'Casos construídos para o estudo. O mesmo caso passa pelas três visões.', 'C1 · C2 · D'],
    MCPTox: ['MCPTox', 'Casos a partir do benchmark MCPTox: ataques escritos na descrição da ferramenta.', 'só C1'],
    Connor: ['Connor', 'Casos a partir do conjunto Connor: servidores maliciosos, com o perigo no código.', 'só C2'],
  };
  const alvo = document.getElementById('conjuntos');
  for (const braco of ['N-INT', 'MCPTox', 'Connor']) {
    const contagem = {};
    CASOS.filter((c) => c.arm === braco).forEach((c) => { contagem[c.cls] = (contagem[c.cls] || 0) + 1; });
    const grade = el('div', { class: 'unidades', role: 'img', 'aria-label': CLASSES.filter(([k]) => contagem[k]).map(([k, nome]) => `${contagem[k]} ${nome}`).join(', ') });
    for (const [k, , cor] of CLASSES) for (let i = 0; i < (contagem[k] || 0); i++) grade.append(el('i', { style: `background:${cor};${k === 'S' ? 'box-shadow:inset 0 0 0 1px #B8C0CC' : ''}` }));
    const total = Object.values(contagem).reduce((a, b) => a + b, 0);
    alvo.append(el('div', { class: 'conjunto' }, [el('h6', { texto: `${info[braco][0]} · ${total} casos` }), el('p', { texto: info[braco][1] }), grade, el('span', { class: 'vistas', texto: `defesas com IA: ${info[braco][2]}` })]));
  }
  document.getElementById('legenda-classes').append(...CLASSES.map(([k, nome, cor]) => el('span', {}, [el('i', { class: 'amostra', style: `background:${cor};${k === 'S' ? 'box-shadow:inset 0 0 0 1px #B8C0CC' : ''}` }), nome])));
}

let grupoT12 = 'P';
let grupoD = 'P';
const DESENHOS = {
  nint: desenharNint,
  connor: () => desenharExterno('cn', 'Connor', 'C2', [['P', (c) => c.cls === 'P'], ['B', (c) => c.cls === 'B'], ['S', (c) => c.cls === 'S']]),
  mcptox: () => desenharExterno('mt', 'MCPTox', 'C1', [['P', (c) => c.cls === 'P'], ['B', (c) => c.cls === 'B'], ['S', (c) => c.cls === 'S']]),
  c1c2() {
    const P_ = resumoTransicoes('C1', 'C2', 'P');
    const B_ = resumoTransicoes('C1', 'C2', 'B');
    const max = maxPar(P_, B_);
    const op = { max, rotuloPiorou: 'acerto → erro', rotuloMelhorou: 'erro → acerto' };
    graficos['g-t12-P'] = divergente(document.getElementById('g-t12-P'), LINHAS, P_, op);
    graficos['g-t12-B'] = divergente(document.getElementById('g-t12-B'), LINHAS, B_, op);
    chaveCores('chave-t12', CAT_T);
    montarGrade('grade-t12', 'detalhe-t12', grupoT12, (p, c, rep) => transicao(p, c, 'C1', 'C2', rep), CAT_T, ['C1', 'C2']);
  },
  combinacao() {
    chaveCores('chave-d', CAT_D);
    montarGrade('grade-d', 'detalhe-d', grupoD, categoriaD, CAT_D, ['C1', 'C2', 'D']);
  },
  consistencia: montarConsistencia,
  'custo-modelo': desenharCustoModelo,
  'custo-camada': desenharCustoCamada,
  'custo-camada-modelo': desenharCustoCamadaModelo,
  erros: desenharErros,
};

function segmentado(id, atributo, aoEscolher) {
  const grupo = document.getElementById(id);
  grupo.addEventListener('click', (ev) => {
    const b = ev.target.closest(`button[${atributo}]`);
    if (!b) return;
    grupo.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    aoEscolher(b.getAttribute(atributo));
  });
}

// ---------- navegação ----------
const telas = [...document.querySelectorAll('section.tela')];
const ids = telas.map((t) => t.id);
let atual = 0;
const desenhadas = new Set();
let fontesProntas = null;

function montarIndice() {
  const indice = document.getElementById('indice');
  let grupoAtual = null;
  let lista = null;
  telas.forEach((t, i) => {
    if (t.dataset.grupo !== grupoAtual) {
      grupoAtual = t.dataset.grupo;
      lista = el('ol');
      indice.append(el('div', {}, [el('h3', { texto: grupoAtual }), lista]));
    }
    lista.append(el('li', {}, el('a', { href: `#${t.id}`, 'data-ir': t.id }, [el('span', { class: 'n', texto: String(i + 1).padStart(2, '0') }), el('span', { texto: t.dataset.curto })])));
  });
}

async function desenhar(id) {
  if (desenhadas.has(id) || !DESENHOS[id]) return;
  desenhadas.add(id);
  const precisaG2 = !['consistencia', 'combinacao'].includes(id);
  if (precisaG2 && typeof G2 === 'undefined') {
    document.querySelectorAll(`#${id} .grafico`).forEach((g) => { g.textContent = 'Gráfico indisponível: a biblioteca G2 não carregou.'; });
    if (id === 'c1c2' || id === 'combinacao' || id === 'erros') { try { if (id === 'erros') listarErros(); } catch (e) { console.error(e); } }
    return;
  }
  await fontesProntas;
  try { DESENHOS[id](); } catch (erro) { console.error(erro); }
}

function redesenharVisiveis() {
  const tela = telas[atual];
  tela.querySelectorAll('.grafico').forEach((g) => { const item = graficos[g.id]; if (item && item.atualizar) { try { item.atualizar(); } catch (e) { console.error(e); } } });
}

function mostrar(indice, { focar = true } = {}) {
  atual = Math.max(0, Math.min(telas.length - 1, indice));
  telas.forEach((t, i) => { t.hidden = i !== atual; });
  const tela = telas[atual];
  document.querySelectorAll('#indice a').forEach((a) => a.setAttribute('aria-current', String(a.dataset.ir === tela.id)));
  document.getElementById('onde').innerHTML = `<b>Tela ${atual + 1} de ${telas.length}</b> · ${tela.dataset.grupo}`;
  const ant = document.getElementById('anterior');
  const prox = document.getElementById('proximo');
  ant.hidden = atual === 0;
  prox.hidden = atual === telas.length - 1;
  if (atual > 0) ant.querySelector('span').textContent = `${atual} · ${telas[atual - 1].dataset.curto}`;
  if (atual < telas.length - 1) prox.querySelector('span').textContent = `${atual + 2} · ${telas[atual + 1].dataset.curto}`;
  try { history.replaceState(null, '', `#${tela.id}`); } catch (e) { /* sem ação */ }
  fecharIndice();
  if (focar) { window.scrollTo({ top: 0 }); tela.setAttribute('tabindex', '-1'); tela.focus({ preventScroll: true }); }
  const jaDesenhada = desenhadas.has(tela.id);
  desenhar(tela.id).then(() => { if (jaDesenhada) redesenharVisiveis(); });
}
const irPara = (id) => { const i = ids.indexOf(id); if (i >= 0) mostrar(i); };
function abrirIndice() { document.body.classList.add('indice-aberto'); document.getElementById('abrir-indice').setAttribute('aria-expanded', 'true'); }
function fecharIndice() { document.body.classList.remove('indice-aberto'); document.getElementById('abrir-indice').setAttribute('aria-expanded', 'false'); }
function alternarProjecao() {
  const ativo = document.body.classList.toggle('projecao');
  document.getElementById('modo-projecao').setAttribute('aria-pressed', String(ativo));
  requestAnimationFrame(redesenharVisiveis);
}

function iniciar() {
  fontesProntas = Promise.race([
    Promise.all(['400 12px "IBM Plex Sans"', '600 12px "IBM Plex Sans"', '700 12px "IBM Plex Sans"'].map((f) => document.fonts.load(f))).catch(() => null),
    new Promise((r) => setTimeout(r, 2500)),
  ]);
  montarIndice();
  montarConjuntos();
  montarFiltros();

  segmentado('grupo-nint', 'data-grupo', (g) => { grupoNint = g; if (desenhadas.has('nint')) desenharNint(); });
  segmentado('grupo-t12', 'data-grupo', (g) => { grupoT12 = g; montarGrade('grade-t12', 'detalhe-t12', grupoT12, (p, c, rep) => transicao(p, c, 'C1', 'C2', rep), CAT_T, ['C1', 'C2']); });
  segmentado('grupo-d', 'data-grupo', (g) => { grupoD = g; if (desenhadas.has('combinacao')) DESENHOS.combinacao(); });
  segmentado('escopo-camada', 'data-escopo', (e) => { escopoCamada = e; if (desenhadas.has('custo-camada')) desenharCustoCamada(); });
  segmentado('escopo-cm', 'data-escopo', (e) => { escopoCm = e; if (desenhadas.has('custo-camada-modelo')) desenharCustoCamadaModelo(); });

  document.addEventListener('click', (ev) => { const alvo = ev.target.closest('[data-ir]'); if (alvo) { ev.preventDefault(); irPara(alvo.dataset.ir); } });
  document.getElementById('anterior').addEventListener('click', () => mostrar(atual - 1));
  document.getElementById('proximo').addEventListener('click', () => mostrar(atual + 1));
  document.getElementById('abrir-indice').addEventListener('click', () => (document.body.classList.contains('indice-aberto') ? fecharIndice() : abrirIndice()));
  document.getElementById('modo-projecao').addEventListener('click', alternarProjecao);
  const termos = document.getElementById('termos');
  document.getElementById('abrir-termos').addEventListener('click', () => termos.showModal());
  document.getElementById('fechar-termos').addEventListener('click', () => termos.close());
  termos.addEventListener('click', (ev) => { if (ev.target === termos) termos.close(); });

  document.addEventListener('keydown', (ev) => {
    if (ev.altKey || ev.ctrlKey || ev.metaKey || termos.open) return;
    if (ev.target.closest('input, textarea, select')) return;
    if (['ArrowRight', 'PageDown'].includes(ev.key)) { ev.preventDefault(); mostrar(atual + 1); }
    else if (['ArrowLeft', 'PageUp'].includes(ev.key)) { ev.preventDefault(); mostrar(atual - 1); }
    else if (ev.key === 'Home') { ev.preventDefault(); mostrar(0); }
    else if (ev.key === 'End') { ev.preventDefault(); mostrar(telas.length - 1); }
    else if (ev.key.toLowerCase() === 't') { termos.showModal(); }
    else if (ev.key.toLowerCase() === 'p') { alternarProjecao(); }
    else if (ev.key === 'Escape') { fecharIndice(); }
  });
  let espera = null;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(redesenharVisiveis, 200); });

  const inicial = ids.indexOf(location.hash.slice(1));
  mostrar(inicial >= 0 ? inicial : 0, { focar: false });
}

iniciar();
