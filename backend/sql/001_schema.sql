-- InventariAR / Atividade 2 — executar em PostgreSQL 14+ INDEPENDENTE.
-- Não altera o banco Cloud existente. Sem dados fictícios ou credenciais.
-- Executar com psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f backend/sql/001_schema.sql
-- Script inicial, intencionalmente não destrutivo: falha se as tabelas já existem.
BEGIN;
CREATE SCHEMA IF NOT EXISTS inventariar;

CREATE TABLE inventariar.categorias (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- Identificador da categoria.
    nome varchar(120) NOT NULL UNIQUE, -- Nome reutilizado por vários equipamentos.
    CONSTRAINT categoria_nome_valido CHECK (length(btrim(nome)) > 0)
);
CREATE TABLE inventariar.locais (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- Identificador da localização.
    nome varchar(160) NOT NULL UNIQUE, -- Sala, bloco ou setor informado no cadastro.
    CONSTRAINT local_nome_valido CHECK (length(btrim(nome)) > 0)
);
CREATE TABLE inventariar.equipamentos (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- Identificador estável usado na API.
    tombamento varchar(80) NOT NULL UNIQUE, -- Código patrimonial único.
    nome varchar(200) NOT NULL, -- Nome ou descrição curta apresentada na lista.
    categoria_id bigint NOT NULL REFERENCES inventariar.categorias(id), -- Categoria normalizada.
    local_id bigint NOT NULL REFERENCES inventariar.locais(id), -- Localização atual normalizada.
    status varchar(10) NOT NULL DEFAULT 'ativo', -- Situação operacional atual.
    condicao varchar(12) NOT NULL DEFAULT 'excelente', -- Estado de conservação atual.
    criado_em timestamptz NOT NULL DEFAULT now(), -- Data real de cadastro para gráfico mensal.
    CONSTRAINT tombamento_nao_vazio CHECK (length(btrim(tombamento)) > 0),
    CONSTRAINT nome_nao_vazio CHECK (length(btrim(nome)) > 0),
    CONSTRAINT status_permitido CHECK (status IN ('ativo', 'inativo')),
    CONSTRAINT condicao_permitida CHECK (condicao IN ('excelente', 'bom', 'aceitavel', 'regular', 'ruim'))
);
CREATE TABLE inventariar.usuarios (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), -- Identificador da conta local.
    nome varchar(120) NOT NULL, -- Nome exibido na interface.
    email varchar(254) NOT NULL, -- E-mail usado para entrar; armazenado em letras minúsculas.
    senha_hash text NOT NULL, -- Hash da senha; a senha original nunca é armazenada.
    criado_em timestamptz NOT NULL DEFAULT now(), -- Data de criação da conta.
    CONSTRAINT usuario_nome_valido CHECK (length(btrim(nome)) > 0),
    CONSTRAINT usuario_email_valido CHECK (email = lower(email) AND position('@' in email) > 1)
);
CREATE UNIQUE INDEX usuarios_email_unico_idx ON inventariar.usuarios (lower(email));
CREATE TABLE inventariar.movimentacoes (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- Identificador do evento de histórico.
    equipamento_id bigint NOT NULL REFERENCES inventariar.equipamentos(id) ON DELETE CASCADE, -- Exclusão definitiva também exclui o histórico (CRUD acadêmico).
    local_origem_id bigint NOT NULL REFERENCES inventariar.locais(id), -- Local antes da operação.
    local_destino_id bigint NOT NULL REFERENCES inventariar.locais(id), -- Local depois da operação.
    status_anterior varchar(10) NOT NULL, -- Status antes da operação.
    status_novo varchar(10) NOT NULL, -- Status depois da operação.
    condicao_anterior varchar(12) NOT NULL, -- Condição antes da operação.
    condicao_nova varchar(12) NOT NULL, -- Condição depois da operação.
    motivo varchar(500) NOT NULL CHECK (length(btrim(motivo)) > 0), -- Justificativa visível da transferência ou atualização.
    realizado_por uuid NOT NULL REFERENCES inventariar.usuarios(id), -- Conta local que registrou o evento.
    realizado_em timestamptz NOT NULL DEFAULT now(), -- Instante do evento.
    CHECK (status_anterior IN ('ativo', 'inativo') AND status_novo IN ('ativo', 'inativo')),
    CHECK (condicao_anterior IN ('excelente', 'bom', 'aceitavel', 'regular', 'ruim') AND condicao_nova IN ('excelente', 'bom', 'aceitavel', 'regular', 'ruim'))
);
-- PK/UNIQUE já criam índices. Estes atendem JOIN, filtros e histórico.
CREATE INDEX equipamentos_categoria_idx ON inventariar.equipamentos(categoria_id);
CREATE INDEX equipamentos_local_idx ON inventariar.equipamentos(local_id);
CREATE INDEX equipamentos_status_condicao_idx ON inventariar.equipamentos(status, condicao);
CREATE INDEX equipamentos_criado_idx ON inventariar.equipamentos(criado_em);
CREATE INDEX movimentacoes_equipamento_data_idx ON inventariar.movimentacoes(equipamento_id, realizado_em DESC);
CREATE INDEX movimentacoes_origem_idx ON inventariar.movimentacoes(local_origem_id);
CREATE INDEX movimentacoes_destino_idx ON inventariar.movimentacoes(local_destino_id);

CREATE VIEW inventariar.vw_patrimonio AS
SELECT e.id, e.tombamento, e.nome, c.nome AS categoria, l.nome AS local,
       e.status, e.condicao, e.criado_em
FROM inventariar.equipamentos e
JOIN inventariar.categorias c ON c.id = e.categoria_id
JOIN inventariar.locais l ON l.id = e.local_id;

-- Sem COMMIT interno: CALL e demais comandos Flask participam da MESMA transação.
-- Bloqueio por equipamento impede transferências concorrentes com histórico incorreto.
CREATE PROCEDURE inventariar.registrar_movimentacao(
    p_equipamento_id bigint, p_local_id bigint, p_status text,
    p_condicao text, p_motivo text, p_autor uuid
)
LANGUAGE plpgsql AS $$
DECLARE anterior inventariar.equipamentos%ROWTYPE;
BEGIN
    IF p_motivo IS NULL OR length(btrim(p_motivo)) NOT BETWEEN 1 AND 500 OR p_autor IS NULL
       OR p_status IS NULL OR p_status NOT IN ('ativo', 'inativo')
       OR p_condicao IS NULL OR p_condicao NOT IN ('excelente', 'bom', 'aceitavel', 'regular', 'ruim') THEN
        RAISE EXCEPTION 'Dados da movimentação inválidos' USING ERRCODE = '22023';
    END IF;
    SELECT * INTO anterior FROM inventariar.equipamentos WHERE id = p_equipamento_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Equipamento não encontrado' USING ERRCODE = 'P0002'; END IF;
    IF p_local_id IS NULL OR NOT EXISTS (SELECT 1 FROM inventariar.locais WHERE id = p_local_id) THEN
        RAISE EXCEPTION 'Local de destino inválido' USING ERRCODE = '22023';
    END IF;
    UPDATE inventariar.equipamentos SET local_id = p_local_id, status = p_status, condicao = p_condicao
    WHERE id = p_equipamento_id;
    INSERT INTO inventariar.movimentacoes
      (equipamento_id, local_origem_id, local_destino_id, status_anterior, status_novo,
       condicao_anterior, condicao_nova, motivo, realizado_por)
    VALUES (p_equipamento_id, anterior.local_id, p_local_id, anterior.status, p_status,
            anterior.condicao, p_condicao, btrim(p_motivo), p_autor);
END;
$$;

-- Procedure de relatório consulta de verdade a VIEW com JOIN e devolve um cursor.
CREATE PROCEDURE inventariar.gerar_relatorio(INOUT resultado refcursor)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN resultado FOR
    SELECT categoria, local, condicao, status, count(*) AS quantidade
    FROM inventariar.vw_patrimonio
    GROUP BY categoria, local, condicao, status
    ORDER BY categoria, local, condicao, status;
END;
$$;
-- Exemplo executável, o cursor existe somente dentro da transação:
-- BEGIN;
-- CALL inventariar.gerar_relatorio('relatorio');
-- FETCH ALL FROM relatorio;
-- COMMIT;
-- O usuário que executa o script é o proprietário; configure DATABASE_URL para
-- esse usuário local. Não concedemos acesso público nem alteramos papéis Cloud.
COMMIT;
