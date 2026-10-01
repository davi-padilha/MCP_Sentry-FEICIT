from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/banner-direita-proposta.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial', boldItalic='Arial-Bold')
source = PdfReader(ROOT / 'materiais-apresentacao/feicit/banners/banner-direita.pdf')
W, H = float(source.pages[0].mediabox.width), float(source.pages[0].mediabox.height)
VW, VH = 1120, 2050
buf = BytesIO()
c = canvas.Canvas(buf, pagesize=(W,H))
c.setTitle('MCP Sentry - proposta para o lado direito do banner')
c.setAuthor('Proposta editorial para a equipe MCP Sentry')
c.scale(W/VW, H/VH)
c.setFillColorRGB(0.0647, 0.1412, 0.2706)
c.rect(0,0,VW,VH,fill=1,stroke=0)

def box(x,y,w,h,r=22):
    c.setFillColorRGB(1,1,1); c.setStrokeColorRGB(0,0,0); c.setLineWidth(2.7)
    c.roundRect(x,VH-y-h,w,h,r,fill=1,stroke=1)

def para(text,x,y,w,size=21,leading=29,align=TA_JUSTIFY,bold=False):
    st=ParagraphStyle('p',fontName='Arial-Bold' if bold else 'Arial',fontSize=size,leading=leading,alignment=align,textColor='#111111')
    p=Paragraph(text,st); _,h=p.wrap(w,1000); p.drawOn(c,x,VH-y-h)
    return y+h

def header(text,y,size=34):
    box(47,y,1026,64)
    para(text,60,y+10,1000,size,42,TA_CENTER,True)

def node(text,x,y,w,h=60,size=19):
    box(x,y,w,h,5)
    p=Paragraph(text,ParagraphStyle('node',fontName='Arial',fontSize=size,leading=size+5,alignment=TA_CENTER))
    _,ph=p.wrap(w-20,h); p.drawOn(c,x+10,VH-y-(h+ph)/2)

def arrow(points):
    c.setStrokeColorRGB(0,0,0); c.setFillColorRGB(0,0,0); c.setLineWidth(2.1)
    p=c.beginPath(); p.moveTo(points[0][0],VH-points[0][1])
    for x,y in points[1:]:p.lineTo(x,VH-y)
    c.drawPath(p)
    import math
    x,y=points[-1]; a,b=points[-2]; angle=math.atan2(y-b,x-a)
    q=c.beginPath(); q.moveTo(x,VH-y)
    for offset in (-0.43,0.43):
        q.lineTo(x-10*math.cos(angle+offset),VH-(y-10*math.sin(angle+offset)))
    q.close();c.drawPath(q,fill=1,stroke=0)

header('MCP SENTRY - DA PESQUISA À APLICAÇÃO',47,33)
box(108,132,904,793)
para('A pesquisa motivou uma aplicação prática: verificar se um servidor MCP local continua correspondente à versão aprovada antes de iniciá-lo. O MCP Sentry atua entre o cliente de IA e o servidor, comparando arquivos, configuração e metadados. Se houver mudança, mantém o servidor parado e oferece evidências para revisão. <b>A IA recomenda; o operador decide sobre a versão revisada.</b> A execução autorizada utiliza uma cópia verificada dos arquivos selecionados.',128,151,864,21,29)
para('Fluxo operacional do MCP Sentry',128,359,864,22,29,TA_CENTER,True)
node('CLIENTE DE IA',435,406,250,49)
node('SENTRY VERIFICA A VERSÃO',390,488,340,59)
arrow([(560,455),(560,488)])
arrow([(560,547),(560,575)])
c.setFillColorRGB(1,1,1);c.setStrokeColorRGB(0,0,0)
p=c.beginPath();p.moveTo(560,VH-575);p.lineTo(650,VH-620);p.lineTo(560,VH-665);p.lineTo(470,VH-620);p.close();c.drawPath(p,fill=1,stroke=1)
para('Mudou?',510,605,100,21,27,TA_CENTER,True)
arrow([(470,620),(299,620),(299,694)])
para('Não',320,587,75,19,25,TA_CENTER)
node('CÓPIA VERIFICADA<br/>INICIAR SERVIDOR',150,694,300,74)
arrow([(650,620),(806,620),(806,647)])
para('Sim',690,587,75,19,25,TA_CENTER)
node('BLOQUEAR E GERAR EVIDÊNCIAS',652,647,308,53,18)
arrow([(806,700),(806,722)])
node('REVISÃO ASSISTIDA POR IA',652,722,308,53,18)
arrow([(806,775),(806,797)])
node('DECISÃO DO OPERADOR<br/>Sem autorização: manter bloqueado',652,797,308,62,17)
arrow([(652,829),(510,829),(299,829),(299,768)])
para('Se autorizado:<br/>revalidar a versão',326,779,245,18,24,TA_CENTER)
para('Escopo: rota local e arquivos configurados. Catálogo conferido após a inicialização, antes das chamadas.',127,879,866,17,23,TA_CENTER)

header('EVOLUÇÃO PROPOSTA - INTEGRAÇÃO NATIVA',950,32)
box(108,1036,904,246)
para('O gateway é uma prova de conceito de um controle que poderia integrar o próprio cliente de IA: verificar mudanças antes de iniciar o servidor e reunir evidências, análise e decisão no mesmo fluxo de uso. A referência e a autorização devem permanecer protegidas contra alterações pelo agente.',128,1053,864,21,28)
para('<b>Hoje:</b> cliente de IA → gateway Sentry → servidor local<br/><b>Proposta:</b> cliente com controle integrado → servidor local',128,1175,864,21,30,TA_CENTER)
para('<b>Integração nativa: proposta futura, ainda não implementada.</b>',128,1246,864,18,24,TA_CENTER)

header('CONCLUSÕES',1306,36)
box(47,1392,1026,255)
end=para('No núcleo N-INT, a combinação de interface e código bloqueou <b>84% das mudanças perigosas</b> e permitiu <b>88% das benignas</b>, entre as decisões válidas. Esses resultados pertencem aos cenários avaliados e não demonstram eficácia universal.<br/><br/>Além da bateria experimental, o trabalho produziu um gateway que coloca a verificação de mudanças no caminho de execução. Há registros técnicos de bloqueio antes do início em cenários controlados.<br/><br/>A validação completa da candidata atual em clientes reais permanece pendente. Como evolução, propõe-se integrar esse controle ao cliente de IA, preservando a decisão do operador.',74,1407,972,20,25)
assert end <= 1635, end
c.showPage();c.save()
result=PdfReader(buf).pages[0]
# Preserve the complete original references area, including heading and bibliography.
refs=source.pages[0]
refs.trimbox=RectangleObject([0,0,W, H*(388/VH)])
refs.cropbox=RectangleObject([0,0,W,H*(388/VH)])
result.merge_page(refs)
writer=PdfWriter();writer.add_page(result)
with OUT.open('wb') as f:writer.write(f)
print(OUT)
print('Conclusion bottom (virtual pixels):',end)

