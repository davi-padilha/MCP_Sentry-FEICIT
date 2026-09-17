import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import vm from 'node:vm';

const html = fs.readFileSync('dist/index.html', 'utf8');
const js = fs.readFileSync('dist/painel.js', 'utf8');
const dataText = fs.readFileSync('dist/dados.js', 'utf8');
const d = JSON.parse(dataText.match(/^const DADOS = (.*);/)[1]);
const original = JSON.parse(fs.readFileSync('original.html', 'utf8').match(/const DADOS = (.*);\r?\n/)[1]);
new vm.Script(js);
new vm.Script(dataText);
assert.deepEqual(d.unidades, original.unidades, 'As decisões e justificativas devem permanecer intactas.');
assert.deepEqual(d.custos, original.custos, 'Os custos devem permanecer intactos.');
assert.equal((html.match(/<section class="tela"/g)||[]).length, 11);
assert.ok(!/<h4>Fonte<\/h4>|Leitura descritiva pós-hoc|\bguarda\b|\b[PBS][01]\b|perigo sutil|perigo explícito|legítima comum|legítima com sinal de risco/.test(html));
assert.ok(!/pos\.data|p\.data/.test(js));
assert.ok(d.posicoes.every(p => !('data' in p) && !p.detalhe.includes('esforço')));
assert.deepEqual(d.posicoes.filter(p => p.nome.includes('Luna')).map(p => p.detalhe), ['baixo', 'alto']);
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
assert.equal(ids.length, new Set(ids).size, 'IDs de elementos devem ser únicos.');
for (const m of js.matchAll(/getElementById\('([^']+)'\)/g)) assert.ok(ids.includes(m[1]), `Elemento ausente: ${m[1]}`);
for (const m of html.matchAll(/(?:src|href)="([^"#:]+)"/g)) {
 if (/^https?:/.test(m[1])) continue;
 assert.ok(fs.existsSync(path.join('dist',m[1])), `Arquivo local ausente: ${m[1]}`);
}
for (const id of ['desenho','erros']) {
 const section = html.match(new RegExp(`<section[^>]+id="${id}"[\\s\\S]*?<\\/section>`))[0];
 assert.ok(!section.includes('class="cuidado"'));
}
const units = new Map(d.unidades.map(u => [u.slice(0,4).join('|'),u]));
const totalR3 = { acertos:0, erros:0, inconclusivas:0 };
const pairFiles = [
 '../pesquisa/02_resultados/01_campanha_principal/dados_brutos/RESULTADOS_COMPLETOS.jsonl',
 '../pesquisa/02_resultados/02_extensao_multimodelo/dados_brutos/RESULTADOS_COMPLETOS.jsonl',
];
let officialR3 = 0;
for (const file of pairFiles) for (const line of fs.readFileSync(file,'utf8').trim().split(/\r?\n/)) {
 const pair=JSON.parse(line); if(!pair.r3_diagnostic)continue;
 const pi=d.posicoes.findIndex(p => p.id===pair.position_id);
 const ci=d.casos.findIndex(c => 'm23c-'+c.id===pair.case_id || c.id===pair.case_id);
 assert.ok(pi>=0 && ci>=0, 'R3 oficial não encontrado no painel.');
 const u=units.get([pi,ci,pair.condition,'R3'].join('|'));
 assert.ok(u, 'Resultado R3 ausente.');
 const action=u[4]==='INC'?'inconclusiva':['VP','FP'].includes(u[4])?'bloquear':'permitir';
 assert.equal(action,pair.r3_action);
 officialR3++;
 if(action==='inconclusiva')totalR3.inconclusivas++;
 else totalR3[action===d.casos[ci].gt?'acertos':'erros']++;
}
assert.equal(officialR3,19);
assert.deepEqual(totalR3,{acertos:10,erros:5,inconclusivas:4});
for(const arm of ['N-INT','Connor','MCPTox']) {
 const cases=d.casos.filter(c => c.arm===arm);
 assert.equal(cases.length,30);
 assert.deepEqual(['P','B','S'].map(cls => cases.filter(c => c.cls===cls).length),[12,12,6]);
}
// Checagem independente dos totais apresentados na tela 6.
const isBin=e => ['VP','VN','FP','FN'].includes(e);
const isOk=e => ['VP','VN'].includes(e);
for(const [group,total,preserved] of [['P',142,138],['B',177,161]]) {
 let n=0,kept=0;
 d.casos.forEach((c,ci) => { if(c.arm!=='N-INT'||c.cls!==group)return;
  d.posicoes.forEach((p,pi) => { for(const rep of ['R1','R2']) {
   const [a,b,e]=['C1','C2','D'].map(cond => units.get([pi,ci,cond,rep].join('|'))[4]);
   if(![a,b,e].every(isBin) || ![a,b].some(isOk))continue;
   n++; if(isOk(e))kept++;
  }});
 }); assert.equal(n,total); assert.equal(kept,preserved);
}
console.log('Verificado: 11 telas, arquivos locais, referências de elementos, decisões e custos preservados.');
console.log('R3 conferida nos registros oficiais: 10 acertos, 5 erros, 4 inconclusivas.');
console.log('Grupos reunidos: 12 perigosos, 12 legítimos e 6 sem mudança em cada conjunto.');
console.log('Combinação conferida: 138/142 e 161/177 acertos anteriores preservados.');
