"""Confere o Lab 05. Rode de dentro de starter/ (ou solucao/):  python ../verificar.py

1. Testa a regra de escolha do modelo sem chamar o Gemini.
2. Audita dois contratos, um com desvios e um limpo, e compara modelo, tempo e tokens.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, os.getcwd())
load_dotenv(Path.cwd() / "cascata" / ".env")


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


try:
    from cascata import agent as lab
except ModuleNotFoundError:
    falhar("não achei a pasta cascata/. Rode este script de dentro de starter/ ou solucao/.")


# 1. A regra, testada com um estado de mentira (sem gastar chamadas ao Gemini)
def simular(statuses: list[str]) -> tuple[str, int]:
    contexto = SimpleNamespace(state={"compliance": {"politicas": [{"status": s} for s in statuses]}})
    pedido = SimpleNamespace(model=lab.MODELO_FLASH)
    lab.escolher_modelo(contexto, pedido)
    return pedido.model, contexto.state.get("desvios")


if simular(["CONFORME", "NAO_CONFORME"])[1] != 1:
    falhar("TODO 1 pendente: `desvios` deve ter as políticas com status NAO_CONFORME.")
if simular(["CONFORME", "NAO_CONFORME"])[0] != lab.MODELO_PRO:
    falhar("TODO 2 pendente: com desvio, troque llm_request.model para MODELO_PRO.")
if simular(["CONFORME", "CONFORME"])[0] != lab.MODELO_FLASH:
    falhar("TODO 2: sem desvio, o modelo deve continuar o Flash.")
if lab.escolher_modelo not in lab.parecer.canonical_before_model_callbacks:
    falhar("TODO 3 pendente: passe before_model_callback=escolher_modelo para o agente parecer.")
print("✓ regra testada: com desvio → Pro, sem desvio → Flash")

# 2. Dois contratos reais
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    falhar("GOOGLE_CLOUD_PROJECT não definido: crie o arquivo cascata/.env (passo 1 do README).")


async def auditar(texto: str) -> dict:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=lab.root_agent, app_name="lab05")
    session = await runner.session_service.create_session(app_name="lab05", user_id="aluno")
    inicio_parecer, tokens, modelo_real = None, 0, ""
    async for event in runner.run_async(
        user_id="aluno",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=texto)]),
    ):
        if event.author == "compliance":
            inicio_parecer = time.monotonic()
        if event.author == "parecer" and event.usage_metadata:
            tokens += event.usage_metadata.total_token_count or 0
        if event.author == "parecer" and event.model_version:
            modelo_real = event.model_version  # o modelo que de fato respondeu, informado pelo Vertex AI
    tempo = time.monotonic() - (inicio_parecer or time.monotonic())
    session = await runner.session_service.get_session(app_name="lab05", user_id="aluno", session_id=session.id)
    return {**session.state, "tempo": tempo, "tokens": tokens, "modelo_real": modelo_real}


resultados = {}
for nome, arquivo in (("TechNova", "contrato_technova.md"), ("VeloNet", "contrato_velonet.md")):
    print(f"… auditando {nome}")
    try:
        resultados[nome] = asyncio.run(auditar((LAB_DIR / arquivo).read_text(encoding="utf-8")))
    except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
        falhar(f"a chamada ao Gemini falhou: {erro}")

print("-" * 72)
print(f"{'Contrato':10} {'Desvios':>7}  {'Modelo que respondeu':24} {'Tempo':>7} {'Tokens':>7}")
for nome, r in resultados.items():
    print(f"{nome:10} {r['desvios']:>7}  {r['modelo_real']:24} {r['tempo']:6.1f}s {r['tokens']:>7}")
print("-" * 72)
for nome, r in resultados.items():
    print(f"{nome}: {r['parecer'].strip().splitlines()[0]}")
print("-" * 72)

if not resultados["TechNova"]["modelo_real"].startswith(lab.MODELO_PRO):
    falhar("o contrato TechNova tem desvios e deveria ter ido para o Pro.")
if not resultados["VeloNet"]["modelo_real"].startswith(lab.MODELO_FLASH):
    falhar(f"o contrato VeloNet veio com {resultados['VeloNet']['desvios']} desvio(s) e foi para o Pro. "
           "Rode de novo: o compliance às vezes é rigoroso demais.")
print("✓ o Pro só entrou onde havia risco. Lab 05 concluído!")
