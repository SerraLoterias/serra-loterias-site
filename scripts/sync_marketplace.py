#!/usr/bin/env python3

import asyncio
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

URL = "https://loteriasonline.caixa.gov.br/silce-web/#/bolao-caixa/20002"

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "boloes.json"
DIAG = BASE / "data" / "ultima_pagina.txt"


async def main():
    respostas = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1440, "height": 1400},
        )

        page = await context.new_page()

        async def capturar(response):
            url = response.url

            palavras = [
                "bolao",
                "bolão",
                "cota",
                "loter",
                "silce",
                "20002",
            ]

            if not any(palavra in url.lower() for palavra in palavras):
                return

            try:
                tipo = response.headers.get("content-type", "")

                if "json" in tipo.lower():
                    conteudo = await response.json()
                else:
                    texto = await response.text()
                    conteudo = texto[:15000]

                respostas.append({
                    "status": response.status,
                    "url": url,
                    "content_type": tipo,
                    "conteudo": conteudo,
                })

            except Exception as erro:
                respostas.append({
                    "status": response.status,
                    "url": url,
                    "erro": str(erro),
                })

        page.on("response", capturar)

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=90000,
        )

        await page.wait_for_timeout(3000)

        # Confirmação de maioridade
        for seletor in [
            'button:has-text("Sim")',
            'a:has-text("Sim")',
            'text="Sim"',
        ]:
            try:
                botao = page.locator(seletor).first

                if await botao.is_visible(timeout=1000):
                    await botao.click()
                    await page.wait_for_timeout(2500)
                    break

            except Exception:
                pass

        # Garante que estamos na página da lotérica
        if "bolao-caixa/20002" not in page.url:
            await page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=90000,
            )

        await page.wait_for_timeout(12000)

        # Faz a página carregar conteúdos que aparecem ao rolar
        for _ in range(8):
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(800)

        corpo = await page.locator("body").inner_text()

        agora = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        ).strftime("%d/%m/%Y %H:%M")

        # Nesta etapa ainda não inventamos bolões.
        # Primeiro vamos descobrir a resposta correta da CAIXA.
        payload = {
            "fonte": URL,
            "lotérica": "Serra Loterias",
            "codigo_loterica": "20002",
            "atualizado_em": agora,
            "boloes": [],
        }

        OUT.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        diagnostico = {
            "pagina_final": page.url,
            "texto_pagina": corpo[:30000],
            "respostas_rede": respostas,
        }

        DIAG.write_text(
            json.dumps(
                diagnostico,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        print(
            f"Diagnóstico concluído. "
            f"{len(respostas)} respostas da CAIXA capturadas."
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
