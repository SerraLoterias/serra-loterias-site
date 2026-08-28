#!/usr/bin/env python3

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "boloes.json"

API_URL = "https://conectalot.com.br/api/boloes"
TOKEN = os.environ.get("CONECTALOG_TOKEN")


def carregar_boloes():
    if not TOKEN:
        raise RuntimeError("Secret CONECTALOG_TOKEN não encontrado.")

    params = {
        "jogo": "all",
        "t": "future",
        "sort": "1",
    }

    url = API_URL + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "User-Agent": "SerraLoteriasSite/1.0",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Erro na API ConectaLot: HTTP {response.status}"
            )

        return json.loads(response.read().decode("utf-8"))


def normalizar(item):
    jogo = item.get("jogo") or {}

    loterica = item.get("loterica") or {}
    cotas = item.get("cotas") or {}

    modalidade = (
        jogo.get("nome")
        or jogo.get("slug")
        or item.get("modalidade")
        or "Bolão"
    )

    concurso = (
        item.get("concurso")
        or item.get("numero_concurso")
        or item.get("n")
    )

    valor_cota = (
        item.get("valor_cota")
        or item.get("valor")
        or item.get("preco")
    )

    descricao = (
        item.get("titulo")
        or item.get("nome")
        or item.get("descricao")
        or "Bolão disponível"
    )

    premio = (
        item.get("premio")
        or item.get("premio_estimado")
        or item.get("estimativa_premio")
    )

    data_sorteio = (
        item.get("data_sorteio")
        or item.get("sorteio")
        or item.get("data")
    )

    restantes = (
        cotas.get("restantes")
        or cotas.get("disponiveis")
    )

    total = cotas.get("total")

    if restantes is not None and total is not None:
        disponibilidade = f"Restam {restantes} de {total} cotas"
    elif restantes is not None:
        disponibilidade = f"{restantes} cotas disponíveis"
    else:
        disponibilidade = "Disponível"

    return {
        "id": item.get("id"),
        "modalidade": modalidade,
        "concurso": concurso,
        "premio_estimado": premio,
        "data_sorteio": data_sorteio,
        "descricao": descricao,
        "valor_cota": valor_cota,
        "disponibilidade": disponibilidade,
        "loterica": {
            "nome": loterica.get("nome"),
            "codigo_ul": loterica.get("codigo_ul"),
        },
        "cotas": cotas,
    }


def main():
    resposta = carregar_boloes()

    itens = (
        resposta.get("data")
        if isinstance(resposta, dict)
        else resposta
    )

    if not isinstance(itens, list):
        raise RuntimeError(
            "Formato inesperado retornado pela API da ConectaLot."
        )

    boloes = []

    for item in itens:
        if isinstance(item, dict):
            boloes.append(normalizar(item))

    agora = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%d/%m/%Y %H:%M")

    payload = {
        "fonte": "ConectaLot API",
        "atualizado_em": agora,
        "quantidade": len(boloes),
        "boloes": boloes,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)

    OUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"{len(boloes)} bolões sincronizados "
        f"pela API da ConectaLot em {agora}."
    )


if __name__ == "__main__":
    main()
