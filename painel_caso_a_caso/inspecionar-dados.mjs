import fs from 'node:fs';
const d = JSON.parse(fs.readFileSync('dist/dados.js', 'utf8').match(/^const DADOS = (.*);/)[1]);
const r3 = d.unidades.filter(u => u[3] === 'R3');
console.log('R3:', JSON.stringify(r3.map(([p, c, cond, rep, est]) => ({ modelo: d.posicoes[p].nome + ' ' + d.posicoes[p].detalhe, caso: d.casos[c].id, cond, est }))));
console.log('Totais R3:', JSON.stringify(r3.reduce((t,u) => { t[u[4]] = (t[u[4]]||0)+1; return t; }, {})));
console.log('Inconclusivas MCPTox:', JSON.stringify(d.posicoes.map((p,i) => ({ modelo: p.nome+' '+p.detalhe, inconclusivas: d.unidades.filter(u => u[0]===i && d.casos[u[1]].arm==='MCPTox' && u[3]!=='R3' && u[4]==='INC').map(u => ({grupo:d.casos[u[1]].cls,just:u[5]})) })).filter(x => x.inconclusivas.length)));
console.log('Falhas MCPTox:', JSON.stringify(d.unidades.filter(u => d.casos[u[1]].arm==='MCPTox' && u[3]!=='R3' && u[4].startsWith('F:')).reduce((t,u) => { const k=d.posicoes[u[0]].nome+'|'+d.casos[u[1]].cls+'|'+u[4]; t[k]=(t[k]||0)+1; return t; },{})));
const byKey = new Map(d.unidades.map(u => [u.slice(0,4).join('|'),u[4]]));
const bin = e => ['VP','VN','FP','FN'].includes(e);
const ok = e => ['VP','VN'].includes(e);
for (const group of ['P','B']) {
 const n={total:0,fora:0,todos_acertam:0,todos_erram:0,melhorou:0,piorou:0,resgatou:0,perdeu_ambos:0,preservou:0,antes_acerto:0};
 d.casos.forEach((c,ci) => { if(c.arm!=='N-INT'||c.cls!==group)return;
  d.posicoes.forEach((p,pi) => { for(const r of ['R1','R2']) {
   const [a,b,e] = ['C1','C2','D'].map(cond => byKey.get([pi,ci,cond,r].join('|')));
   if(![a,b,e].every(bin)){n.fora++;continue;} n.total++;
   const before=ok(a)+ok(b);
   if(before){n.antes_acerto++;if(ok(e))n.preservou++;}
   if(ok(e)){if(before===2)n.todos_acertam++;else{n.melhorou++;if(before===0)n.resgatou++;}}
   else {if(before===0)n.todos_erram++;else{n.piorou++;if(before===2)n.perdeu_ambos++;}}
  }});
 }); console.log('D '+group+':', JSON.stringify(n));
}
