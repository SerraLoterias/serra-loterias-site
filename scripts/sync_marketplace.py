#!/usr/bin/env python3
import asyncio, json, re, os
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://loteriasonline.caixa.gov.br/silce-web/#/bolao-caixa/20002"
OUT = Path(__file__).resolve().parents[1] / "data" / "boloes.json"

MODS = ["Mega-Sena","Lotofácil","+Milionária","Milionária","Quina","Lotomania",
        "Timemania","Dupla Sena","Dia de Sorte","Super Sete"]

def money(s):
    m = re.search(r'R\$\s*[\d\.\,]+', s or "")
    return m.group(0).replace("  "," ") if m else None

def parse_text(text):
    clean = " ".join((text or "").split())
    modality = next((m for m in MODS if m.lower() in clean.lower()), None)
    if not modality:
        return None

    concurso = None
    mc = re.search(r'(?:concurso|conc\.?)\s*[:ºn°\-]*\s*(\d{3,5})', clean, re.I)
    if mc: concurso = mc.group(1)

    values = re.findall(r'R\$\s*[\d\.\,]+', clean)
    valor_cota = values[-1] if values else None

    # Try to infer pool description.
    desc = None
    patterns = [
        r'(\d+\s+jogos?\s+(?:de\s+)?\d+\s+números?)',
        r'(\d+\s+jogos?)',
        r'(\d+\s+números?)',
    ]
    for p in patterns:
        md = re.search(p, clean, re.I)
        if md:
            desc = md.group(1)
            break

    # Availability / quotas.
    disponibilidade = None
    ma = re.search(r'((?:restam|dispon[ií]ve(?:l|is)|cotas?)[^R$]{0,45})', clean, re.I)
    if ma: disponibilidade = ma.group(1).strip()

    # Date
    data_sorteio = None
    md = re.search(r'\b(\d{2}/\d{2}(?:/\d{2,4})?)\b', clean)
    if md: data_sorteio = md.group(1)

    # Prize: first large money value may be estimate, but only if more than one R$ exists.
    premio = values[0] if len(values) > 1 else None

    return {
        "modalidade": modality,
        "concurso": concurso,
        "premio_estimado": premio,
        "data_sorteio": data_sorteio,
        "descricao": desc or "Bolão disponível",
        "valor_cota": valor_cota,
        "disponibilidade": disponibilidade or "Disponível no marketplace",
        "texto_origem": clean[:500]
    }

async def accept_age(page):
    # Multiple versions of CAIXA page use "Sim" for age confirmation.
    for selector in [
        'button:has-text("Sim")', 'a:has-text("Sim")',
        'text="Sim"'
    ]:
        try:
            loc = page.locator(selector).first
            if await loc.is_visible(timeout=1500):
                await loc.click()
                await page.wait_for_timeout(1200)
                return
        except Exception:
            pass

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1440, "height": 1400},
        )
        page = await context.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        await accept_age(page)
        # Restore route after age dialog if needed.
        if "bolao-caixa/20002" not in page.url:
            await page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(8000)

        # Scroll to force lazy content.
        for _ in range(7):
            await page.mouse.wheel(0, 1200)
            await page.wait_for_timeout(700)

        # Gather card-like text. Broad selectors make this resilient to markup changes.
        texts = await page.locator("article, li, .card, [class*='card'], [class*='bolao'], [class*='bolão']").all_inner_texts()
        if not texts:
            texts = await page.locator("body").all_inner_texts()

        parsed, seen = [], set()
        for t in texts:
            b = parse_text(t)
            if not b:
                continue
            key = (b["modalidade"], b["concurso"], b["descricao"], b["valor_cota"])
            if key in seen:
                continue
            # Keep only blocks that actually look commercial / pool-like.
            low = t.lower()
            if not ("r$" in low or "cota" in low or "bolão" in low or "bolao" in low):
                continue
            seen.add(key)
            parsed.append(b)

        now = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
        payload = {
            "fonte": URL,
            "lotérica": "Serra Loterias",
            "codigo_loterica": "20002",
            "atualizado_em": now,
            "boloes": parsed,
        }

        OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(OUT)

        # Diagnostics for selector changes.
        (OUT.parent/"ultima_pagina.txt").write_text((await page.locator("body").inner_text())[:50000], encoding="utf-8")
        await browser.close()

        print(f"{len(parsed)} bolões capturados em {now}.")
        if not parsed:
            # Do not fail workflow: site will show direct CAIXA fallback.
            print("Aviso: nenhum card foi reconhecido; revisar ultima_pagina.txt.")

if __name__ == "__main__":
    asyncio.run(main())
