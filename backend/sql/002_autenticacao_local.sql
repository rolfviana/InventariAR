-- InventariAR: adiciona contas locais ao schema existente sem apagar dados.
BEGIN;

CREATE TABLE IF NOT EXISTS inventariar.usuarios (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), -- Identificador da conta local.
    nome varchar(120) NOT NULL, -- Nome exibido na interface.
    email varchar(254) NOT NULL, -- E-mail em letras minúsculas usado para entrar.
    senha_hash text NOT NULL, -- Hash da senha; a senha original não é armazenada.
    criado_em timestamptz NOT NULL DEFAULT now(), -- Data de criação da conta.
    CONSTRAINT usuario_nome_valido CHECK (length(btrim(nome)) > 0),
    CONSTRAINT usuario_email_valido CHECK (email = lower(email) AND position('@' in email) > 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS usuarios_email_unico_idx
    ON inventariar.usuarios (lower(email));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'movimentacoes_realizado_por_fkey'
          AND conrelid = 'inventariar.movimentacoes'::regclass
    ) THEN
        ALTER TABLE inventariar.movimentacoes
            ADD CONSTRAINT movimentacoes_realizado_por_fkey
            FOREIGN KEY (realizado_por) REFERENCES inventariar.usuarios(id) NOT VALID;
    END IF;
END;
$$;

COMMIT;
