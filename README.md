# Teste — Solicitações (Backend / Fullstack)

Recorte de um sistema de solicitações: formulário dinâmico no navegador, API FastAPI + SQL Server, código sequencial `SOL-AAAA-NNNN` sem duplicar em concorrência, e claim atômico de um agendador.

## O que tem no projeto

| Pasta | Conteúdo |
|---|---|
| `banco/` | Scripts para criar o banco e as tabelas |
| `backend/` | API FastAPI, `connect.py` e teste dos dois workers |
| `frontend/` | Página vanilla (HTML/CSS/JS) com `esc()` |

## Pré-requisitos

- Python 3.11+
- SQL Server Express (instância `localhost\SQLEXPRESS`)
- [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- SSMS (opcional, para inspecionar as tabelas)

## 1. Banco de dados

No SSMS, conecte em `localhost\SQLEXPRESS` com autenticação do Windows.

1. Execute `banco/01_criar_banco.sql` (cria o banco `solicitacoes`).
2. Execute `banco/02_criar_tabelas.sql` (cria as tabelas e os dados de exemplo).

Tabelas:

- `solicitacao` — pedidos; respostas do formulário em JSON (`dados`)
- `contador_solicitacao` — último número do código `SOL-AAAA-NNNN` por ano
- `schema_campo` — planta do formulário (título, setor, prioridade, descrição)
- `agendamento` — fila do claim atômico dos workers

## 2. Backend

```powershell
cd backend
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Ajuste `SQLSERVER_CONN` em `.env` se a instância ou o driver forem diferentes. O `.env` não vai para o Git.

Suba a API:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000/

## 3. Endpoints

| Método | Caminho | Função |
|---|---|---|
| `GET` | `/schema-campos` | Campos do formulário |
| `GET` | `/solicitacoes` | Lista solicitações |
| `GET` | `/solicitacoes/{codigo}` | Abre uma solicitação |
| `POST` | `/solicitacoes` | Cria solicitação (`SOL-AAAA-NNNN`) |
| `GET` | `/agendamentos` | Lista agendamentos |
| `POST` | `/agendamentos/{id}/reivindicar` | Claim atômico |

Exemplo de `POST /solicitacoes`:

```json
{
  "dados": {
    "titulo": "Troca de cadeira",
    "setor": "RH",
    "prioridade": "media",
    "descricao": "A cadeira quebrou"
  }
}
```

## 4. Front

A página pede `/schema-campos`, monta o formulário, envia o `POST` e abre o painel de uma solicitação. Todo valor vindo da API passa por `esc()` antes de entrar no HTML (proteção contra XSS armazenado).

## 5. Concorrência (dois workers)

```powershell
cd backend
..\.venv\Scripts\python.exe dois_workers.py
```

Os dois workers leem o mesmo `proxima_execucao` e disputam o `UPDATE ... WHERE proxima_execucao = valor_lido`. Só um ganha; o outro altera zero linhas.

O código `SOL-AAAA-NNNN` usa trava na linha do ano (`UPDLOCK`, `HOLDLOCK`) dentro da mesma transação do `INSERT`, para dois `POST` ao mesmo tempo não gerarem o mesmo número.

## 6. Pontos de segurança do teste

| Problema | Como o projeto trata |
|---|---|
| XSS armazenado | `esc()` no `frontend/app.js` |
| SQL concatenado | parâmetros `?` no `pyodbc` |
| Token em log | não logar Authorization / cookie / segredos |

## Estrutura

```text
.
├── banco/
│   ├── 01_criar_banco.sql
│   └── 02_criar_tabelas.sql
├── backend/
│   ├── connect.py          # context manager + transação
│   ├── main.py             # FastAPI
│   ├── dois_workers.py     # claim atômico
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── README.md
```
