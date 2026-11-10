# InventariAR

Projeto acadêmico de Rodolfo Viana e Yngride Gabrielle Nascimento Santos para controle de patrimônio, desenvolvido no contexto da atividade de Desenvolvimento Web e Banco de Dados.

A primeira versão visual foi criada no Lovable. Para execução local, a interface foi reconstruída em HTML, CSS e JavaScript e integrada à API Flask e ao PostgreSQL. Esta versão local não inclui todos os recursos da versão visual original, como câmera e realidade aumentada.

## Estrutura

- `backend/`: API REST em Flask e script PostgreSQL.
- `frontend/`: interface em HTML, CSS e JavaScript, consumindo a API em JSON.
- `docs/`: explicação complementar do projeto para estudo e apresentação.

O roteiro explicativo está em `docs/explicacao_inventariar.pdf`. Ele registra a equipe, explica a API e inclui capturas dos testes realizados no ambiente local.

## Requisitos

- Python 3.10 ou superior.
- PostgreSQL 14 ou superior.
- Nenhum serviço de autenticação externo é necessário; as contas ficam no PostgreSQL local.

## Configuração local

Crie o ambiente Python e instale as dependências:

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Configure o endereço da API no frontend. O exemplo já aponta para o serviço local:

```powershell
Copy-Item frontend\config.example.js frontend\config.js
```

`frontend/config.js` e `backend/.env` são arquivos locais e não devem ser enviados ao GitHub. Não publique senhas, tokens ou URLs de conexão com credenciais.

## Banco de dados

Instale PostgreSQL 14+ e inicie o serviço local. Se o banco ainda não estiver configurado, o script pede a senha local de `postgres` sem mostrá-la, cria o banco `inventariar` quando necessário e aplica os scripts SQL. Se a conexão já estiver salva em `backend/.env`, ele usa essa conexão para instalar as atualizações sem pedir a senha novamente.

```powershell
backend\.venv\Scripts\python.exe backend\setup_local_db.py
```

O primeiro script cria o schema `inventariar`, as tabelas normalizadas, a view `vw_patrimonio`, as constraints e as procedures. O segundo adiciona o cadastro local de usuários. O configurador preserva os dados existentes e cria uma chave privada de sessão no arquivo local `.env`.

O endereço web do pgAdmin do IFRO é uma interface administrativa, não a conexão PostgreSQL consumida pela API. Para usar um banco remoto, o servidor precisa aceitar conexões de rede do computador da API; o servidor informado não aceitou conexão direta pela porta padrão durante a verificação. Por isso, para executar a aplicação neste computador, use o PostgreSQL local.

## API Flask

Depois de configurar o banco, inicie a API a partir da raiz do projeto:

```powershell
backend\.venv\Scripts\python.exe backend\run.py
```

O arquivo `backend/.env` é configurado pelo script de banco. `CORS_ORIGINS` deve incluir `http://localhost:8080` para executar a interface local.

A API fica em `http://127.0.0.1:5000`. `GET /api/health` verifica o acesso ao banco. O cadastro e o login estão em `POST /api/auth/register` e `POST /api/auth/login`. As rotas de equipamentos exigem um token temporário emitido pela própria API.

## Testes automatizados

Na raiz do workspace:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Esses testes verificam validações, tokens locais e respostas JSON sem alterar o banco de dados. Para conferir também a conexão real com PostgreSQL, consulte `/api/health`.

Para recriar o PDF explicativo, instale a dependência de documentação e execute:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r docs\requirements.txt
backend\.venv\Scripts\python.exe docs\generate_explanation.py
```

### Endpoints principais

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/api/health` | Verificar API e banco |
| POST | `/api/auth/register` | Criar conta local |
| POST | `/api/auth/login` | Entrar na conta local |
| GET | `/api/equipamentos` | Listar e pesquisar |
| GET | `/api/equipamentos/<id>` | Consultar um equipamento |
| POST | `/api/equipamentos` | Cadastrar |
| PUT / PATCH | `/api/equipamentos/<id>` | Atualizar |
| DELETE | `/api/equipamentos/<id>` | Excluir |
| POST | `/api/equipamentos/<id>/movimentacoes` | Registrar movimentação pela procedure |
| GET | `/api/equipamentos/<id>/movimentacoes` | Consultar histórico |
| GET | `/api/relatorios/patrimonio` | Agrupar patrimônio pela view |

O relatório pode ser testado pela API. A procedure `inventariar.gerar_relatorio` é um exercício de banco separado e não precisa ser chamada pela API, conforme o enunciado.

## Frontend local

Depois de copiar `frontend/config.example.js` para `frontend/config.js`, a interface aponta para a API local em `http://127.0.0.1:5000`. Não é necessário configurar conta ou serviço externo de login.

Em outro terminal, na raiz do workspace:

```powershell
python -m http.server 8080 --directory frontend
```

Abra `http://localhost:8080` e escolha “Criar conta”. As senhas são armazenadas no banco somente como hash; o token de acesso fica na sessão atual do navegador.

## Testes manuais sugeridos

1. Abra `http://127.0.0.1:5000/api/health` e confirme a resposta JSON `{"status":"ok","fonte":"PostgreSQL"}`.
2. Entre na interface e confira se a lista carrega do PostgreSQL.
3. Crie um equipamento com `POST /api/equipamentos`.
4. Pesquise e consulte o registro com `GET`.
5. Edite o registro com `PUT` e depois registre uma movimentação.
6. Confira a view/relatório em `GET /api/relatorios/patrimonio`.
7. Teste tombamento duplicado e valores inválidos; a API deve responder com erro JSON, sem salvar a operação.

## Requisitos da atividade

| Requisito | Onde está | Como explicar/verificar |
|---|---|---|
| Flask e mensagens JSON | `backend/inventariar/` | Iniciar com `python run.py` e testar no navegador ou Postman |
| PK, FK e normalização | `backend/sql/001_schema.sql` | Ver tabelas de categorias, locais, equipamentos e movimentações |
| Pelo menos três `CHECK` | `backend/sql/001_schema.sql` | Conferir tombamento/nome, status, condição e motivo |
| Procedure utilizada pela API | `registrar_movimentacao` e rota de movimentação | Comparar o local/status antes e depois do `POST` |
| View com `JOIN` e procedure de relatório | `vw_patrimonio` e `gerar_relatorio` | Executar os comandos de exemplo comentados no SQL |
| CRUD e relatório | `backend/inventariar/routes.py` | Fazer os testes manuais listados acima |
| Configuração centralizada | `backend/.env.example` e `frontend/config.example.js` | Criar arquivos locais sem versionar valores de ambiente |
| Integração visual | `frontend/` | Abrir a interface e observar os pedidos JSON à API |

As telas locais foram simplificadas para facilitar o estudo: login, visão geral, listagem/pesquisa, cadastro, edição, exclusão e movimentação. Recursos de câmera e realidade aumentada da versão visual original não foram reconstruídos.
