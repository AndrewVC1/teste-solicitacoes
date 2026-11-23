import os
from contextlib import contextmanager
from pathlib import Path

import pyodbc


def _carregar_env() -> None:
    """Lê backend/.env se existir. Não sobrescreve variável já definida."""
    arquivo = Path(__file__).with_name(".env")
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(chave.strip(), valor)


def string_conexao() -> str:
    _carregar_env()
    valor = os.environ.get("SQLSERVER_CONN")
    if not valor:
        raise RuntimeError(
            "Defina SQLSERVER_CONN em backend/.env. Exemplo: "
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost\\SQLEXPRESS;DATABASE=solicitacoes;"
            "Trusted_Connection=yes;TrustServerCertificate=yes"
        )
    return valor


def todas(cursor) -> list[dict]:
    colunas = [coluna[0] for coluna in cursor.description]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def uma(cursor) -> dict | None:
    linha = cursor.fetchone()
    if linha is None:
        return None
    colunas = [coluna[0] for coluna in cursor.description]
    return dict(zip(colunas, linha))


@contextmanager
def conexao():
    """Abre uma conexão com o SQL Server e uma transação.

    autocommit=False segura o INSERT do contador e o INSERT da
    solicitação até o commit. Se der erro, rollback desfaz os dois.
    """
    conn = pyodbc.connect(string_conexao(), autocommit=False)
    try:
        cursor = conn.cursor()
        cursor.execute("SET NOCOUNT ON")
        cursor.close()
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
