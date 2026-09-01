#!/usr/bin/env python3

import json
import os
import urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "resultados.json"

API_BASE = "https://conectalot.com.br/api"
TOKEN = os.environ.get("CONECTALOG_TOKEN")

JOGOS = {
    "Mega-Sena": "megasena",
    "Quina": "quina",
    "Mais Milionária": "maismilionaria",
    "Lotofácil": "lotofacil",
    "Lotomania": "lotomania",
    "Timemania": "timemania",
    "Dupla Sena": "duplasena",
    "Federal": "federal",
    "Loteca": "loteca",
    "Dia de Sorte": "diadesorte",
    "Super Sete": "supersete",
}


def api_get(endpoint):
    url = f"{API_BASE}/{endpoint}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "SerraLoteriasSite/1.0",
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalizar(nome, endpoint, dados):
    if endpoint == "loteca":
    print("DEBUG LOTECA:", json.dumps(dados, ensure_ascii=False, indent=2))
    dezenas = (
        dados.get("dezenas_na_string")
        or dados.get("dezenas_sorteadas")
        or dados.get("dezenas")
        or []
    )

    if endpoint == "duplasena":
       primeiro = dados.get("dezenas_sorteadas1") or []
       segundo = dados.get("dezenas_sorteadas2") or []

       dezenas = []
       if primeiro:
           dezenas.append("1º: " + " - ".join(str(x) for x in primeiro))
       if segundo:
           dezenas.append("2º: " + " - ".join(str(x) for x in segundo))
    if isinstance(dezenas, list):
        dezenas = [str(x) for x in dezenas]
    elif isinstance(dezenas, str):
        dezenas = [
            x.strip()
            for x in dezenas.replace(";", ",").split(",")
            if x.strip()
        ]

    return {
        "modalidade": nome,
        "endpoint": endpoint,
        "concurso": dados.get("id") or dados.get("concurso"),
        "data": (
            dados.get("data_formatada")
            or dados.get("data_apuracao")
        ),
   "dezenas": dezenas,

"time_coracao": (
    dados.get("nome_time_coracao")
    or dados.get("time_coracao")
    or dados.get("nomeTimeCoracaoMesSorte")
    or dados.get("nome_time_coracao_mes_sorte")
),

"mes_sorte": (
    dados.get("mes_sorte")
    or dados.get("mesDaSorte")
    or dados.get("mes_sorteado")
    or dados.get("mesSorte")
    or dados.get("nome_mes_sorte")
),

"acumulado": dados.get("acumulado"),
        "valor_arrecadado": dados.get("valor_arrecadado"),
        "proximo_concurso": dados.get("prox_concurso"),
        "data_proximo_concurso": (
            dados.get("data_proximo_concurso_formatada")
            or dados.get("data_proximo_concurso")
        ),
        "valor_estimado_proximo_concurso": (
            dados.get("valor_estimado_prox_concurso")
        ),
    }


def main():
    resultados = []

    for nome, endpoint in JOGOS.items():
        try:
            dados = api_get(endpoint)

            if isinstance(dados, dict) and isinstance(dados.get("data"), dict):
                dados = dados["data"]

            if endpoint == "duplasena":
                print("DEBUG DUPLA SENA:", json.dumps(dados, ensure_ascii=False, indent=2))
    
            if isinstance(dados, dict):
                resultados.append(
                    normalizar(nome, endpoint, dados)
                )

        except Exception as erro:
            print(f"Aviso: erro ao carregar {nome}: {erro}")

    agora = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%d/%m/%Y %H:%M")

    payload = {
        "fonte": "ConectaLot API",
        "atualizado_em": agora,
        "quantidade": len(resultados),
        "resultados": resultados,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
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
        f"{len(resultados)} resultados sincronizados "
        f"pela API da ConectaLot em {agora}."
    )


if __name__ == "__main__":
    main()
