import fs from 'node:fs';
import path from 'node:path';

// Importação mecânica do painel público: separa a aplicação do runtime do Claude.
const root = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1'));
const source = fs.readFileSync(path.join(root, 'original.html'), 'utf8');
let product = source.slice(source.indexOf('<title>MCP Sentry caso a caso'));
const css = product.match(/<style>([\s\S]*?)<\/style>/)[1];
const app = product.match(/<script>\s*(const DADOS = [\s\S]*?)<\/script>/)[1];
const dataMatch = app.match(/^const DADOS = (.*);\r?\n/);
const data = JSON.parse(dataMatch[1]);
for (const p of data.posicoes) {
  delete p.data;
  if (p.nome.includes('Luna')) {
    p.detalhe = p.detalhe.includes('alto') ? 'alto' : 'baixo';
  } else if (p.detalhe.includes('esforço')) {
    p.detalhe = '';
  }
}
for (const c of data.casos) c.cls = c.cls[0] === 'P' ? 'P' : c.cls[0] === 'B' ? 'B' : 'S';
product = product.replace(/<style>[\s\S]*?<\/style>/, '<link rel="stylesheet" href="estilo.css">');
product = product.replace(/<script>\s*const DADOS = [\s\S]*?<\/script>/, '<script src="dados.js"></script>\n<script src="painel.js"></script>');
product = product.replace('https://cdn.jsdelivr.net/npm/@antv/g2@5.4.8/dist/g2.min.js', 'vendor/g2.min.js');
product = product.replace(/\s*<div><h4>Fonte<\/h4><p class="fonte">.*?<\/p><\/div>/g, '');
const headEnd = product.indexOf('<div class="casca">');
const html = '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
  + product.slice(0, headEnd).trim() + '\n</head>\n<body>\n' + product.slice(headEnd);
fs.mkdirSync(path.join(root, 'dist', 'vendor'), { recursive: true });
fs.writeFileSync(path.join(root, 'dist', 'index.html'), html);
fs.writeFileSync(path.join(root, 'dist', 'estilo.css'), css.trim() + '\n');
fs.writeFileSync(path.join(root, 'dist', 'dados.js'), 'const DADOS = ' + JSON.stringify(data) + ';\n');
fs.writeFileSync(path.join(root, 'dist', 'painel.js'), app.slice(dataMatch[0].length).trim() + '\n');
console.log(`Painel importado: ${data.posicoes.length} configurações, ${data.casos.length} casos, ${data.unidades.length} decisões.`);
