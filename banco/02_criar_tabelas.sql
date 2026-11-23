-- Passo 2. Execute este arquivo inteiro depois que o banco solicitacoes existir.
-- USE troca a consulta para esse banco.

USE solicitacoes;
GO

-- Último número do código SOL-AAAA-NNNN, uma linha por ano.
-- A API trava esta linha (UPDLOCK, HOLDLOCK) dentro da transação
-- para dois POST ao mesmo tempo não gerarem o mesmo código.
CREATE TABLE contador_solicitacao (
    ano    int NOT NULL PRIMARY KEY,
    ultimo int NOT NULL
);
GO

-- A solicitação. "dados" guarda o JSON com as respostas do formulário.
CREATE TABLE solicitacao (
    id        int IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    codigo    varchar(20)  NOT NULL UNIQUE,
    status    varchar(30)  NOT NULL CONSTRAINT DF_solicitacao_status DEFAULT 'aberta',
    dados     nvarchar(max) NOT NULL CONSTRAINT DF_solicitacao_dados DEFAULT N'{}',
    criado_em datetime2    NOT NULL CONSTRAINT DF_solicitacao_criado DEFAULT SYSUTCDATETIME()
);
GO

-- Campos que o front usa para montar o formulário.
CREATE TABLE schema_campo (
    id          int IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    nome        varchar(50)   NOT NULL UNIQUE,
    rotulo      nvarchar(100) NOT NULL,
    tipo        varchar(20)   NOT NULL,
    obrigatorio bit           NOT NULL CONSTRAINT DF_schema_obrigatorio DEFAULT 0,
    opcoes      nvarchar(max) NULL,
    ordem       int           NOT NULL
);
GO

-- Fila do agendador. O claim atômico compara proxima_execucao com o valor lido.
-- datetime2(6) para no microssegundo, que é o que o Python consegue ler e devolver igual.
CREATE TABLE agendamento (
    id               int IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    nome             nvarchar(100) NOT NULL,
    proxima_execucao datetime2(6)  NOT NULL,
    status           varchar(30)   NOT NULL CONSTRAINT DF_agendamento_status DEFAULT 'pendente',
    worker_id        varchar(50)   NULL
);
GO

INSERT INTO schema_campo (nome, rotulo, tipo, obrigatorio, opcoes, ordem) VALUES
    ('titulo',     N'Título',     'texto',       1, NULL, 1),
    ('setor',      N'Setor',      'selecao',     1, N'["TI", "RH", "Financeiro"]', 2),
    ('prioridade', N'Prioridade', 'selecao',     1, N'["baixa", "media", "alta"]', 3),
    ('descricao',  N'Descrição',  'texto_longo', 0, NULL, 4);
GO

INSERT INTO agendamento (nome, proxima_execucao)
VALUES (N'lembrete de solicitacao', SYSUTCDATETIME());
GO
