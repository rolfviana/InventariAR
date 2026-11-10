import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "explicacao_inventariar.pdf"

FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
pdfmetrics.registerFont(TTFont("ArialPT", str(FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("ArialPT-Bold", str(FONT_DIR / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("ArialPT-Italic", str(FONT_DIR / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("ArialPT-BoldItalic", str(FONT_DIR / "arialbi.ttf")))
pdfmetrics.registerFontFamily(
    "ArialPT",
    normal="ArialPT",
    bold="ArialPT-Bold",
    italic="ArialPT-Italic",
    boldItalic="ArialPT-BoldItalic",
)
pdfmetrics.registerFont(TTFont("ConsolasPT", str(FONT_DIR / "consola.ttf")))

INK = colors.HexColor("#18302d")
GREEN = colors.HexColor("#1a765e")
PALE = colors.HexColor("#edf5f1")
MUTED = colors.HexColor("#63716d")
LINE = colors.HexColor("#dce4df")
WARNING = colors.HexColor("#fff5d8")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CoverTitle", parent=styles["Title"], fontName="ArialPT-Bold",
    fontSize=23, leading=29, textColor=INK, alignment=TA_CENTER, spaceAfter=12,
))
styles.add(ParagraphStyle(
    name="CoverSub", parent=styles["Normal"], fontName="ArialPT",
    fontSize=12, leading=17, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading1"], fontName="ArialPT-Bold",
    fontSize=16, leading=20, textColor=INK, spaceBefore=8, spaceAfter=9,
))
styles.add(ParagraphStyle(
    name="Subsection", parent=styles["Heading2"], fontName="ArialPT-Bold",
    fontSize=11.5, leading=15, textColor=GREEN, spaceBefore=8, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BodyPT", parent=styles["BodyText"], fontName="ArialPT",
    fontSize=9.4, leading=13.2, textColor=INK, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="SmallPT", parent=styles["BodyText"], fontName="ArialPT",
    fontSize=8, leading=10.5, textColor=MUTED, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="TableHead", parent=styles["BodyText"], fontName="ArialPT-Bold",
    fontSize=8, leading=10, textColor=colors.white,
))
styles.add(ParagraphStyle(
    name="TableCell", parent=styles["BodyText"], fontName="ArialPT",
    fontSize=7.8, leading=10.2, textColor=INK,
))
styles.add(ParagraphStyle(
    name="CodePT", fontName="ConsolasPT", fontSize=7.5, leading=9.5,
    textColor=INK, backColor=PALE, borderColor=LINE, borderWidth=0.5,
    borderPadding=7, leftIndent=4, rightIndent=4, spaceBefore=3, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Callout", parent=styles["BodyText"], fontName="ArialPT",
    fontSize=9, leading=12.5, textColor=INK, backColor=WARNING,
    borderColor=colors.HexColor("#ecd58b"), borderWidth=0.6,
    borderPadding=8, spaceBefore=5, spaceAfter=9,
))


def para(text, style="BodyPT"):
    return Paragraph(escape(text), styles[style])


def rich(text, style="BodyPT"):
    return Paragraph(text, styles[style])


def code(text):
    return Preformatted(text.strip(), styles["CodePT"])


def evidence_figure(number, filename, title, caption):
    image_path = ROOT / "docs" / "capturas" / filename
    image = Image(str(image_path))
    scale = min((174 * mm) / image.imageWidth, (94 * mm) / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return KeepTogether([
        Paragraph(f"Figura {number}. {escape(title)}", styles["Subsection"]),
        image,
        Paragraph(escape(caption), styles["SmallPT"]),
        Spacer(1, 4 * mm),
    ])


def table(rows, widths, header=True):
    converted = []
    for row_index, row in enumerate(rows):
        cell_style = "TableHead" if header and row_index == 0 else "TableCell"
        converted.append([
            Paragraph(escape(str(value)), styles[cell_style]) for value in row
        ])
    result = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), GREEN))
        if len(rows) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]))
    result.setStyle(TableStyle(commands))
    return result


class ArchitectureDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 500
        self.height = 138

    def wrap(self, available_width, available_height):
        self.width = min(available_width, 500)
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        box_width = 112
        box_height = 43
        gap = (self.width - 4 * box_width) / 3
        y = 33
        labels = [
            ("Frontend", "HTML / CSS / JS"),
            ("API Flask", "rotas e JSON"),
            ("PostgreSQL", "schema inventariar"),
            ("Contas locais", "token assinado"),
        ]
        xs = [i * (box_width + gap) for i in range(4)]
        for i, (title, detail) in enumerate(labels):
            canvas.setFillColor(PALE if i != 3 else colors.HexColor("#f5f0ff"))
            canvas.setStrokeColor(GREEN if i != 3 else colors.HexColor("#7964a7"))
            canvas.roundRect(xs[i], y, box_width, box_height, 7, fill=1, stroke=1)
            canvas.setFillColor(INK)
            canvas.setFont("ArialPT-Bold", 9)
            canvas.drawCentredString(xs[i] + box_width / 2, y + 26, title)
            canvas.setFillColor(MUTED)
            canvas.setFont("ArialPT", 7)
            canvas.drawCentredString(xs[i] + box_width / 2, y + 12, detail)

        canvas.setStrokeColor(GREEN)
        canvas.setFillColor(GREEN)
        for left, right in [(0, 1), (1, 2)]:
            start = xs[left] + box_width + 2
            end = xs[right] - 3
            canvas.line(start, y + box_height / 2, end, y + box_height / 2)
            canvas.line(end - 4, y + box_height / 2 + 3, end, y + box_height / 2)
            canvas.line(end - 4, y + box_height / 2 - 3, end, y + box_height / 2)
        canvas.setStrokeColor(colors.HexColor("#7964a7"))
        start = xs[1] + box_width / 2
        end = xs[3] + box_width / 2
        canvas.setDash(3, 2)
        canvas.line(start, y + box_height + 2, start, y + box_height + 18)
        canvas.line(start, y + box_height + 18, end, y + box_height + 18)
        canvas.line(end, y + box_height + 18, end, y + box_height + 2)
        canvas.setDash()
        canvas.setFillColor(MUTED)
        canvas.setFont("ArialPT", 7)
        canvas.drawCentredString((start + end) / 2, y + box_height + 22, "verifica Bearer token")
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(self.width / 2, 8, "Setas indicam as trocas principais; a API valida o usuário antes das rotas protegidas.")


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("ArialPT", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "InventariAR | Material de estudo - revisar antes da entrega")
    canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Página {document.page}")
    canvas.restoreState()


def build_story():
    story = [
        Spacer(1, 25 * mm),
        para("INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DE RONDÔNIA", "CoverSub"),
        para("Tecnologia em Sistemas para Internet", "CoverSub"),
        Spacer(1, 13 * mm),
        para("InventariAR", "CoverTitle"),
        para("Roteiro de estudo e explicação do projeto", "CoverSub"),
        para("Atividade 2 - Desenvolvimento Web III + Banco de Dados II", "CoverSub"),
        Spacer(1, 12 * mm),
        table([
            ["Identificação", "Informação"],
            ["Ano da atividade", "2026"],
            ["Equipe", "Rodolfo Viana e Yngride Gabrielle Nascimento Santos"],
            ["Responsabilidade e revisão", "Distribuição confirmada pelos integrantes; quadro na seção 7"],
            ["Versão do material", "Adaptação local para estudo e apresentação"],
        ], [42 * mm, 115 * mm]),
        Spacer(1, 12 * mm),
        rich("<b>Importante:</b> este material explica o código que existe neste workspace. A equipe confirmou a distribuição de tarefas apresentada na seção 7. Este é um material de estudo e explicação, com as capturas dos testes realizadas.", "Callout"),
        PageBreak(),

        para("1. O que o sistema faz", "Section"),
        para("O InventariAR organiza equipamentos de patrimônio. Cada registro guarda tombamento, nome, categoria, local atual, condição e status. A interface local mostra um painel, lista pesquisável, cadastro, edição, exclusão e movimentação. As operações de inventário passam pela API Flask em JSON e ficam no PostgreSQL."),
        para("A primeira versão visual do projeto foi criada no Lovable. Depois, a interface foi trazida para este workspace e reconstruída localmente em HTML, CSS e JavaScript para funcionar com a API Flask e o PostgreSQL configurados aqui. Esta versão não é uma exportação completa do projeto Lovable e não inclui os recursos de câmera ou realidade aumentada da versão original."),
        para("Como explicar em voz alta: “O objetivo é registrar os equipamentos e manter a localização e a condição atualizadas. O navegador não acessa o banco diretamente: ele envia requisições para a API, e a API aplica as validações e grava os dados no PostgreSQL.”"),
        para("2. Arquitetura", "Section"),
        ArchitectureDiagram(),
        para("O frontend envia requisições HTTP para a API Flask. O usuário cria uma conta local no PostgreSQL; a senha é armazenada somente como hash. A API entrega um token assinado e verifica esse token nas rotas protegidas, associando o identificador do usuário à movimentação. Nenhum serviço externo de autenticação é necessário."),
        para("GET /api/health verifica o acesso ao PostgreSQL. O cadastro e o login locais emitem um token assinado, com validade de 12 horas, exigido pelas rotas de inventário. A chave de assinatura fica no arquivo local de ambiente e não é versionada."),
        para("3. Banco de dados e integridade", "Section"),
        para("O script principal é backend/sql/001_schema.sql. O modelo separa os dados em cinco tabelas para evitar repetir nomes de categoria e local em cada equipamento, manter as contas locais e registrar o histórico de alterações."),
        table([
            ["Tabela", "Função e relações"],
            ["categorias", "Lista os nomes de categoria. A PK id é referenciada por equipamentos."],
            ["locais", "Lista os nomes de local. A PK id é referenciada por equipamentos e movimentações."],
            ["equipamentos", "Cadastro principal. Tem PK id, tombamento único e FKs categoria_id e local_id."],
            ["usuarios", "Contas locais com nome, e-mail único, hash de senha e identificador UUID."],
            ["movimentacoes", "Histórico ligado ao equipamento, com origem/destino, valores anteriores e novos, motivo, autor e data."],
        ], [38 * mm, 119 * mm]),
        para("PK identifica cada linha. FK aponta para uma linha relacionada e impede referências inexistentes. UNIQUE em tombamento evita dois equipamentos com o mesmo código patrimonial. Os índices apoiam filtros, relações e consultas do histórico."),
        para("As regras CHECK incluem nomes e tombamento não vazios, status limitado a ativo/inativo, condição limitada a cinco valores, motivo obrigatório e validação dos valores anterior/novo no histórico. Existem mais de três CHECKs no script."),
        para("3.1 View e stored procedures", "Subsection"),
        para("A view inventariar.vw_patrimonio combina equipamentos, categorias e locais por JOIN. Assim, a API e o relatório podem ler nomes compreensíveis sem duplicar esses nomes na tabela de equipamentos."),
        para("A procedure inventariar.registrar_movimentacao recebe equipamento, local, status, condição, motivo e autor. Ela bloqueia a linha do equipamento durante a transação, lê os valores anteriores, atualiza os valores atuais e grava o histórico. A rota POST de movimentações chama essa procedure."),
        para("A procedure inventariar.gerar_relatorio abre um cursor consultando a view, agrupando quantidade por categoria, local, condição e status. Ela é executada no próprio banco; o enunciado não exige que a API a chame. O exemplo comentado no SQL mostra BEGIN, CALL, FETCH e COMMIT porque o cursor só existe durante a transação."),
        para("4. API e contrato JSON", "Section"),
        table([
            ["Método e rota", "Comportamento"],
            ["GET /api/health", "Confirma que a API consegue consultar o PostgreSQL."],
            ["POST /api/auth/register", "Cria uma conta local e devolve um token assinado."],
            ["POST /api/auth/login", "Confere e-mail/senha e inicia a sessão local."],
            ["GET /api/equipamentos", "Lista; aceita busca e filtros validados."],
            ["GET /api/equipamentos/<id>", "Consulta um registro."],
            ["POST /api/equipamentos", "Cria e retorna HTTP 201."],
            ["PUT ou PATCH /api/equipamentos/<id>", "Atualiza o cadastro; mudanças de local/status/condição também geram histórico."],
            ["DELETE /api/equipamentos/<id>", "Exclui o equipamento e, pela FK com cascade, seu histórico."],
            ["POST /api/equipamentos/<id>/movimentacoes", "Chama a procedure e retorna o estado atualizado."],
            ["GET /api/equipamentos/<id>/movimentacoes", "Lista o histórico do equipamento."],
            ["GET /api/relatorios/patrimonio", "Agrupa os registros lidos pela view."],
        ], [75 * mm, 82 * mm]),
        para("A API confere o formato e os campos de entrada antes de abrir a operação no banco. Textos são limitados, valores fora das listas permitidas são rejeitados e os erros voltam como JSON com código HTTP. A transação faz commit se a operação termina e rollback quando ocorre uma exceção."),
        para("Exemplo do corpo para criar um registro:", "Subsection"),
        code("""{
  "nome": "Notebook de teste",
  "tombamento": "IFRO-TESTE-001",
  "categoria": "Informática",
  "local": "Laboratório 2",
  "status": "ativo",
  "condicao": "bom"
}"""),
        PageBreak(),
        para("4.1 Como explicar uma requisição da interface até o banco", "Section"),
        para("Um exemplo simples é cadastrar um equipamento. A tela transforma os campos preenchidos em JSON e chama a função api() de frontend/app.js. Essa função usa fetch() para enviar uma requisição HTTP à API. No cadastro, o método é POST e o caminho é /api/equipamentos."),
        table([
            ["Etapa", "O que acontece no projeto"],
            ["1. Interface", "frontend/app.js transforma os valores do formulário em JSON e chama api() com o método POST."],
            ["2. Rota", "O Flask encontra @api.post('/equipamentos') em backend/inventariar/routes.py."],
            ["3. Autenticação e validação", "O decorador @protected confere o token; body() lê JSON e validate_equipment() verifica os campos."],
            ["4. Persistência", "connection() abre uma transação PostgreSQL; comandos SQL parametrizados salvam os dados nas tabelas."],
            ["5. Resposta", "O Flask devolve JSON e HTTP 201; a interface recarrega a lista para mostrar o registro persistido."],
        ], [34 * mm, 123 * mm]),
        para("O símbolo @ é um decorador do Flask. Por exemplo, @api.post('/equipamentos') registra qual função atende uma requisição POST nesse caminho. O decorador @protected executa a autenticação antes da função da rota. Isso evita repetir essa verificação dentro de cada endpoint protegido."),
        para("Os valores SQL são passados separadamente do texto da consulta, usando marcadores %s e uma tupla de parâmetros. Assim, os dados recebidos não são concatenados diretamente no comando SQL. Já os nomes de tabela dinâmicos usados para categorias e locais passam por sql.Identifier, do psycopg."),
        para("A função connection() usa o contexto da conexão para finalizar a transação: se o bloco termina normalmente, há commit; se ocorre uma exceção, há rollback. Erros conhecidos do PostgreSQL são convertidos em respostas da API, como 409 para valor único duplicado, 422 para dados inválidos e 503 quando o banco está indisponível."),
        para("Como explicar uma movimentação", "Subsection"),
        para("Na movimentação, a interface envia POST para /api/equipamentos/<id>/movimentacoes. A rota valida local, condição, status e motivo. Em seguida, a aplicação chama CALL inventariar.registrar_movimentacao(...). A procedure no banco atualiza o equipamento e grava o histórico na mesma transação. Por isso, a resposta 201 só é enviada depois que a operação termina com sucesso."),
        para("A rota também bloqueia a linha do equipamento durante a alteração com SELECT ... FOR UPDATE. Esse bloqueio ajuda a evitar que duas alterações concorrentes leiam e sobrescrevam o mesmo estado ao mesmo tempo."),
        para("Autenticação em palavras simples", "Subsection"),
        para("No cadastro, a API valida os dados e grava o hash da senha, não a senha original. No login, compara a senha informada com o hash guardado. Se estiver correta, emite um token assinado. O frontend envia esse token no cabeçalho Authorization: Bearer ... nas rotas protegidas. A API valida assinatura e prazo; a validade é de 12 horas."),
        para("Um roteiro curto para apresentar", "Subsection"),
        rich("<b>“A interface envia JSON por HTTP para as rotas do Flask. Cada rota confere a autenticação e valida os campos antes de acessar o banco. As consultas são parametrizadas e executadas em uma transação PostgreSQL. Nas movimentações, a API chama uma procedure que atualiza o equipamento e registra o histórico. No fim, a API devolve JSON com um código HTTP, e a tela atualiza os dados.”</b>", "Callout"),
        PageBreak(),
        para("Perguntas comuns sobre a API", "Subsection"),
        table([
            ["Pergunta", "Resposta que você pode explicar"],
            ["Qual a diferença entre GET e POST?", "GET consulta dados; POST envia dados para criar algo ou executar uma ação, como cadastrar ou movimentar."],
            ["O que significa HTTP 201?", "A requisição foi atendida e um novo registro foi criado."],
            ["Por que a senha não é salva diretamente?", "O banco guarda um hash; no login, a senha digitada é comparada usando a função própria de verificação."],
            ["O que acontece se a validação falhar?", "A API não grava os dados e retorna uma mensagem JSON com código HTTP apropriado, como 422."],
            ["Por que usar uma procedure na movimentação?", "Para manter a atualização do equipamento e o registro do histórico juntos no banco."],
        ], [52 * mm, 105 * mm]),
        PageBreak(),

        para("5. Frontend e configuração", "Section"),
        para("A página inicial está em frontend/index.html; o comportamento fica em frontend/app.js e o visual em frontend/styles.css. O arquivo frontend/config.js aponta para a URL local da API e é ignorado pelo Git. Não há URLs externas de autenticação para configurar."),
        para("O backend lê DATABASE_URL, SECRET_KEY e CORS_ORIGINS de backend/.env. O configurador gera a chave privada de sessão. As contas ficam na tabela inventariar.usuarios; a senha original nunca é gravada. O frontend não precisa de chave secreta ou conta de autenticação externa."),
        para("O token de acesso assinado é guardado em sessionStorage durante a sessão atual do navegador e enviado no cabeçalho Authorization. A sessão expira após 12 horas. A interface não usa registros fictícios como resposta alternativa: se a API falhar, mostra a mensagem de erro."),
        para("Como executar com o banco local configurado:", "Subsection"),
        code("""# Terminal 1 - dentro de backend, com o ambiente virtual ativado
python run.py

# Terminal 2 - na raiz do workspace
python -m http.server 8080 --directory frontend

# Abrir no navegador
http://localhost:8080"""),
        para("6. Plano de testes para demonstração", "Section"),
        para("Os testes automatizados verificam validações, tokens e respostas JSON. Também foi realizado um teste integrado no PostgreSQL local: cadastro/login, senha incorreta, cadastro de equipamento, movimentação pela procedure e relatório. Os registros temporários foram removidos ao final. Resultado da suíte automatizada: 10 testes passaram."),
        rich("<b>Escopo das evidências:</b> as capturas a seguir foram feitas durante o teste do frontend local e durante requisições HTTP reais para a API Flask conectada ao PostgreSQL. Os dados usados para a demonstração são temporários; senhas e tokens não aparecem nas imagens.", "Callout"),
        table([
            ["Teste real", "Endpoint", "Resultado"],
            ["Saúde do serviço e conexão com PostgreSQL", "GET /api/health", "HTTP 200; status ok."],
            ["Criar equipamento", "POST /api/equipamentos", "HTTP 201."],
            ["Consultar e atualizar equipamento", "GET e PUT /api/equipamentos/<id>", "HTTP 200."],
            ["Registrar movimentação pela procedure", "POST /api/equipamentos/<id>/movimentacoes", "HTTP 201."],
            ["Consultar histórico e relatório", "GET /api/equipamentos/<id>/movimentacoes; GET /api/relatorios/patrimonio", "HTTP 200."],
            ["Tentar repetir tombamento", "POST /api/equipamentos", "HTTP 409 esperado; duplicidade recusada."],
            ["Excluir registro temporário", "DELETE /api/equipamentos/<id>", "HTTP 200; registro removido."],
        ], [52 * mm, 76 * mm, 29 * mm]),
        para("As telas de cadastro, movimentação, edição e exclusão foram exercitadas pela interface. Os métodos, endpoints e códigos HTTP abaixo foram registrados em requisições reais feitas no navegador. A resposta 409 para tombamento repetido é um bloqueio esperado, não uma falha do teste."),
        PageBreak(),
        para("6.1 Capturas dos testes", "Section"),
        para("Cada figura tem uma legenda para identificar a tela ou requisição testada. As capturas foram feitas durante os testes no ambiente local."),
        evidence_figure(1, "01-cadastro.png", "Criação de conta local", "Tela usada para cadastrar uma conta de teste; a conta temporária foi removida ao concluir a coleta de evidências."),
        evidence_figure(2, "02-painel.png", "Painel após autenticação", "Painel carregado depois do cadastro local; os indicadores usam a resposta da API."),
        PageBreak(),
        evidence_figure(3, "03-api-health.png", "Verificação da API e do PostgreSQL", "GET /api/health respondeu HTTP 200 com status ok e fonte PostgreSQL."),
        evidence_figure(4, "04-equipamento-cadastrado.png", "Leitura do equipamento cadastrado", "Equipamento criado pela interface e apresentado na listagem; operação POST retornou HTTP 201."),
        PageBreak(),
        evidence_figure(5, "05-formulario-movimentacao.png", "Formulário de movimentação", "Formulário preenchido para transferir o equipamento de teste; a ação chama a procedure no banco."),
        evidence_figure(6, "06-movimentacao-concluida.png", "Tela de equipamentos após os testes", "A listagem está vazia após a limpeza do registro temporário. A movimentação pela procedure retornou HTTP 201, conforme o resumo da figura 9."),
        PageBreak(),
        evidence_figure(7, "07-edicao-concluida.png", "Edição do cadastro", "Nome atualizado pela interface e valor persistido na listagem; operação PUT retornou HTTP 200."),
        evidence_figure(8, "08-exclusao-concluida.png", "Exclusão do registro de teste", "A listagem fica vazia após excluir o equipamento temporário; operação DELETE retornou HTTP 200."),
        PageBreak(),
        evidence_figure(9, "09-resultados-api.png", "Resumo das requisições HTTP reais", "Resumo exibido no navegador a partir das respostas reais da API: CRUD, movimentação, histórico, relatório e conflito esperado para tombamento duplicado."),
        para("7. Divisão e dupla revisão", "Section"),
        para("A atividade pede que cada parte tenha um responsável e seja conferida por pelo menos outra pessoa. A equipe confirmou a seguinte distribuição para este roteiro:"),
        table([
            ["Parte", "Responsável", "Conferente (dupla revisão)"],
            ["Modelo relacional, CHECKs, view e procedures", "Rodolfo Viana", "Yngride Gabrielle Nascimento Santos"],
            ["API Flask, rotas JSON e validações", "Yngride Gabrielle Nascimento Santos", "Rodolfo Viana"],
            ["Interface e integração", "Rodolfo Viana", "Yngride Gabrielle Nascimento Santos"],
            ["Documentação, testes e compactação", "Yngride Gabrielle Nascimento Santos", "Rodolfo Viana"],
        ], [67 * mm, 45 * mm, 45 * mm]),
        para("8. Perguntas que podem aparecer", "Section"),
        table([
            ["Pergunta", "Resposta curta"],
            ["Por que separar categoria e local?", "Para reduzir repetição e manter referências consistentes com chaves estrangeiras."],
            ["O que a procedure de movimentação garante?", "Atualiza o equipamento e registra os valores antigos e novos na mesma transação, com bloqueio contra alterações concorrentes."],
            ["Por que a API devolve JSON?", "JSON é o formato de troca usado entre a interface e os endpoints REST."],
            ["Onde está o CRUD?", "Nas rotas de equipamentos: POST cria, GET consulta, PUT/PATCH atualiza e DELETE exclui."],
            ["A procedure de relatório é chamada pela API?", "Não. Ela existe no banco e consulta a view, como permite o enunciado."],
            ["A integração foi testada de ponta a ponta?", "Sim, localmente: cadastro/login, CRUD, procedure de movimentação e relatório foram testados com PostgreSQL."],
        ], [62 * mm, 95 * mm]),
        Spacer(1, 4 * mm),
        rich("<b>Checklist antes de entregar:</b> revisar se a divisão da seção 7 corresponde ao trabalho realizado; confirmar com a professora o uso do banco local; gerar o documento final único e incluir script SQL e código-fonte no ZIP com o nome solicitado.", "Callout"),
    ]
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title="InventariAR - roteiro de estudo e explicação",
        author="Equipe InventariAR",
    )
    doc.build(build_story(), onFirstPage=footer, onLaterPages=footer)
    print(f"PDF gerado: {OUTPUT}")


if __name__ == "__main__":
    main()
