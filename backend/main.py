import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from connect import conexao, todas, uma

app = FastAPI(title="Solicitacoes")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class NovaSolicitacao(BaseModel):
    dados: dict = Field(
        examples=[{"titulo": "Troca de cadeira", "setor": "RH", "prioridade": "media"}]
    )


class Reivindicacao(BaseModel):
    worker_id: str
    proxima_execucao: datetime


def ler_json(valor):
    if valor is None or isinstance(valor, (dict, list)):
        return valor
    return json.loads(valor)


def preparar_solicitacao(linha: dict | None) -> dict | None:
    if linha is not None:
        linha["dados"] = ler_json(linha["dados"])
    return linha


def preparar_campo(linha: dict) -> dict:
    linha["opcoes"] = ler_json(linha["opcoes"])
    linha["obrigatorio"] = bool(linha["obrigatorio"])
    return linha


def gerar_codigo(conn) -> str:
    """Próximo código SOL-AAAA-NNNN, sem duplicar com dois POST juntos.

    UPDLOCK impede outra transação de ler a linha para alterar.
    HOLDLOCK segura essa trava até o commit. A segunda requisição espera,
    lê o número já somado e gera o código seguinte.
    """
    ano = datetime.now().year
    cur = conn.cursor()
    cur.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM contador_solicitacao WITH (UPDLOCK, HOLDLOCK)
            WHERE ano = ?
        )
        INSERT INTO contador_solicitacao (ano, ultimo)
        VALUES (?, 0)
        """,
        ano,
        ano,
    )
    cur.execute(
        """
        UPDATE contador_solicitacao
        SET ultimo = ultimo + 1
        OUTPUT inserted.ultimo
        WHERE ano = ?
        """,
        ano,
    )
    linha = cur.fetchone()
    cur.close()
    if linha is None:
        raise RuntimeError(f"Contador do ano {ano} não foi criado.")
    return f"SOL-{ano}-{linha[0]:04d}"


def validar_dados(conn, dados: dict) -> None:
    cur = conn.cursor()
    cur.execute("SELECT nome, obrigatorio FROM schema_campo")
    campos = todas(cur)
    cur.close()
    conhecidos = {campo["nome"] for campo in campos}
    desconhecidos = sorted(set(dados) - conhecidos)
    if desconhecidos:
        raise HTTPException(
            status_code=422,
            detail=f"Campo desconhecido: {', '.join(desconhecidos)}",
        )
    faltando = [
        campo["nome"]
        for campo in campos
        if campo["obrigatorio"] and not str(dados.get(campo["nome"], "")).strip()
    ]
    if faltando:
        raise HTTPException(
            status_code=422,
            detail=f"Campo obrigatório: {', '.join(faltando)}",
        )


@app.get("/schema-campos")
def listar_schema():
    with conexao() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT nome, rotulo, tipo, obrigatorio, opcoes, ordem
            FROM schema_campo
            ORDER BY ordem
            """
        )
        linhas = [preparar_campo(linha) for linha in todas(cur)]
        cur.close()
        return linhas


@app.get("/solicitacoes")
def listar_solicitacoes():
    with conexao() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, codigo, status, dados, criado_em
            FROM solicitacao
            ORDER BY id DESC
            """
        )
        linhas = [preparar_solicitacao(linha) for linha in todas(cur)]
        cur.close()
        return linhas


@app.get("/solicitacoes/{codigo}")
def obter_solicitacao(codigo: str):
    with conexao() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, codigo, status, dados, criado_em
            FROM solicitacao
            WHERE codigo = ?
            """,
            codigo,
        )
        linha = preparar_solicitacao(uma(cur))
        cur.close()
    if linha is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    return linha


@app.post("/solicitacoes", status_code=201)
def criar_solicitacao(corpo: NovaSolicitacao):
    with conexao() as conn:
        validar_dados(conn, corpo.dados)
        codigo = gerar_codigo(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO solicitacao (codigo, dados)
            OUTPUT inserted.id, inserted.codigo, inserted.status,
                   inserted.dados, inserted.criado_em
            VALUES (?, ?)
            """,
            codigo,
            json.dumps(corpo.dados, ensure_ascii=False),
        )
        criada = preparar_solicitacao(uma(cur))
        cur.close()
        return criada


def reivindicar(conn, agendamento_id: int, proxima_execucao: datetime, worker_id: str) -> bool:
    """Um worker só leva a tarefa se o horário ainda for o que ele leu.

    Os dois leem o mesmo proxima_execucao. Os dois mandam o UPDATE.
    O SQL Server trava a linha: o primeiro grava e troca o horário;
    o segundo não acha mais esse horário e altera zero linhas.
    """
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE agendamento
        SET status = 'em_execucao',
            worker_id = ?,
            proxima_execucao = DATEADD(minute, 5, proxima_execucao)
        OUTPUT inserted.id
        WHERE id = ?
          AND proxima_execucao = ?
          AND status = 'pendente'
        """,
        worker_id,
        agendamento_id,
        proxima_execucao,
    )
    ganhou = cur.fetchone() is not None
    cur.close()
    return ganhou


@app.get("/agendamentos")
def listar_agendamentos():
    with conexao() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, proxima_execucao, status, worker_id
            FROM agendamento
            ORDER BY id
            """
        )
        linhas = todas(cur)
        cur.close()
        return linhas


@app.post("/agendamentos/{agendamento_id}/reivindicar")
def reivindicar_agendamento(agendamento_id: int, corpo: Reivindicacao):
    with conexao() as conn:
        ganhou = reivindicar(
            conn, agendamento_id, corpo.proxima_execucao, corpo.worker_id
        )
    return {"ganhou": ganhou, "worker_id": corpo.worker_id}


frontend = Path(__file__).resolve().parent.parent / "frontend"
if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
