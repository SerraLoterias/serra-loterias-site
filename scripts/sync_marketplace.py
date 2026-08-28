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

API_BASE = "https://conectalot.com.br/api"
TOKEN = os.environ.get("CONECTALOG_TOKEN")


def api_get(path, params=None):
    if not TOKEN:
        raise RuntimeError("Secret CONECTALOG_TOKEN não encontrado.")

    url = API_BASE + path

    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "User-Agent": "SerraLoteriasSite/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Erro na API ConectaLot: HTTP {response.status}"
            )

        return json.loads(
            response.read().decode("utf-8")
        )


def formatar_reais(valor):
    if valor is None:
        return None

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    texto = f"{numero:,.2f}"
    texto = texto.replace(",", "X")
    texto = texto.replace(".", ",")
    texto = texto.replace("X", ".")

    return f"R$ {texto}"


def carregar_lista():
    return api_get(
        "/boloes",
        {
            "jogo": "all",
            "t": "future",
            "sort": "1",
        },
    )


def carregar_detalhe(id_bolao):
    resposta = api_get(
        f"/boloes/{id_bolao}"
    )

    if isinstance(resposta, dict) and isinstance(resposta.get("data"), dict):
        return resposta["data"]

return resposta


def normalizar(item_lista):
    id_bolao = item_lista.get("id")

    detalhe = {}

    if id_bolao:
        try:
            detalhe = carregar_detalhe(id_bolao)
        except Exception as erro:
            print(
                f"Aviso: não foi possível carregar "
                f"detalhes do bolão {id_bolao}: {erro}"
            )

    item = detalhe if isinstance(detalhe, dict) and detalhe else item_lista

    jogo = item.get("jogo") or {}
    loterica = item.get("loterica") or {}
    cotas = item.get("cotas") or {}
    apostas = item.get("apostas") or {}
    valores = item.get("valores") or {}
    status = item.get("status") or {}

    modalidade = (
        jogo.get("nome")
        or jogo.get("slug")
        or "Bolão"
    )

    concurso = item.get("concurso")

    quantidade_jogos = apostas.get("quantidade")
    quantidade_numeros = apostas.get("numeros")

    if quantidade_jogos and quantidade_numeros:
        descricao = (
            f"{quantidade_numeros} números • "
            f"{quantidade_jogos} "
            f"{'jogo' if quantidade_jogos == 1 else 'jogos'}"
        )
    elif quantidade_numeros:
        descricao = f"{quantidade_numeros} números"
    elif quantidade_jogos:
        descricao = (
            f"{quantidade_jogos} "
            f"{'jogo' if quantidade_jogos == 1 else 'jogos'}"
        )
    else:
        descricao = (
            item.get("title")
            or item.get("description")
            or "Bolão disponível"
        )

    valor_cota = formatar_reais(
        valores.get("cota_com_tarifa")
        or valores.get("cota_sem_tarifa")
    )

    premio_estimado = formatar_reais(
        valores.get("premio_estimado")
    )

    restantes = cotas.get("restantes")
    disponiveis = cotas.get("disponiveis")
    total = cotas.get("total")

    if restantes is not None and total is not None:
        disponibilidade = (
            f"Restam {restantes} de {total} cotas"
        )
    elif disponiveis is not None and total is not None:
        disponibilidade = (
            f"{disponiveis} de {total} cotas disponíveis"
        )
    elif disponiveis is not None:
        disponibilidade = (
            f"{disponiveis} cotas disponíveis"
        )
    else:
        disponibilidade = "Disponível"

    finalizado = status.get("finalizado", False)

    return {
        "id": id_bolao,
        "modalidade": modalidade,
        "concurso": concurso,
        "premio_estimado": premio_estimado,
        "descricao": descricao,
        "quantidade_jogos": quantidade_jogos,
        "quantidade_numeros": quantidade_numeros,
        "valor_cota": valor_cota,
        "disponibilidade": disponibilidade,
        "finalizado": finalizado,
        "loterica": {
            "nome": loterica.get("nome"),
            "codigo_ul": loterica.get("codigo_ul"),
            "cidade": loterica.get("cidade"),
            "uf": loterica.get("uf"),
        },
        "cotas": cotas,
        "valores": valores,
        "apostas": apostas,
    }


def main():
    resposta = carregar_lista()

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
        if not isinstance(item, dict):
            continue

        bolao = normalizar(item)

        if not bolao.get("finalizado"):
            boloes.append(bolao)

    agora = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%d/%m/%Y %H:%M")

    payload = {
        "fonte": "ConectaLot API",
        "atualizado_em": agora,
        "quantidade": len(boloes),
        "boloes": boloes,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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
