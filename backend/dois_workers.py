"""Dois workers leem o mesmo horário e só um consegue reivindicar."""

import threading

from connect import conexao, uma
from main import reivindicar


def preparar() -> dict:
    with conexao() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE agendamento
            SET status = 'pendente',
                worker_id = NULL,
                proxima_execucao = SYSUTCDATETIME()
            WHERE id = 1
            """
        )
        cur.execute(
            """
            SELECT id, proxima_execucao
            FROM agendamento
            WHERE id = 1
            """
        )
        linha = uma(cur)
        cur.close()
    return linha


def main() -> None:
    tarefa = preparar()
    barreira = threading.Barrier(2)
    resultado = {}

    def worker(nome: str) -> None:
        barreira.wait()
        with conexao() as conn:
            resultado[nome] = reivindicar(
                conn,
                tarefa["id"],
                tarefa["proxima_execucao"],
                nome,
            )

    threads = [
        threading.Thread(target=worker, args=("worker-a",)),
        threading.Thread(target=worker, args=("worker-b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with conexao() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, worker_id, proxima_execucao FROM agendamento WHERE id = 1"
        )
        final = uma(cur)
        cur.close()

    print(f"worker-a ganhou: {resultado['worker-a']}")
    print(f"worker-b ganhou: {resultado['worker-b']}")
    print(f"quem ficou com a tarefa: {final['worker_id']}")
    print(f"status: {final['status']}")


if __name__ == "__main__":
    main()
