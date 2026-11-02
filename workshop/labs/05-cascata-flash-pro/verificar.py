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


# Um único event loop para todas as chamadas ao Gemini. Com um rodar() por chamada, o cliente
# do Gemini tenta fechar a conexão da chamada anterior num loop já encerrado ("Event loop is closed")
_LOOP = asyncio.new_event_loop()


def rodar(tarefa):
    return _LOOP.run_until_complete(tarefa)


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


try:
    from cascata import agent as lab
except ModuleNotFoundError:
    falhar("não achei a pasta cascata/. Rode este script de dentro de starter/ ou solucao/.")


# 1. A regra, testada com um estado de mentira (sem gastar chamadas ao Gemini)
POLITICAS = ["POL-LGPD-01", "POL-SLA-02", "POL-FIN-03", "POL-JUR-04"]


def simular(reprovadas: list[str]) -> str:
    politicas = [{"politica": c, "status": "NAO_CONFORME" if c in reprovadas else "CONFORME",
                  "motivo": "", "pagina": 1} for c in POLITICAS]
    contexto = SimpleNamespace(state={"compliance": {"politicas": politicas}})
    pedido = SimpleNamespace(model=lab.MODELO_FLASH)
    try:
        lab.escolher_modelo(contexto, pedido)
    except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
        falhar(f"a sua regra deu erro: {type(erro).__name__}: {erro}")
    return pedido.model


if lab.escolher_modelo not in lab.parecer.canonical_before_model_callbacks:
    falhar("TODO 3 pendente: passe before_model_callback=escolher_modelo para o agente parecer.")
CENARIOS = [
    ("nenhum desvio", []),
    ("1 desvio (SLA)", ["POL-SLA-02"]),
    ("1 desvio (jurídico)", ["POL-JUR-04"]),
    ("2 desvios", ["POL-SLA-02", "POL-FIN-03"]),
    ("4 desvios", POLITICAS),
]
print("A sua regra:")
escolhas = {}
for nome, reprovadas in CENARIOS:
    escolhas[nome] = simular(reprovadas)
    print(f"  {nome:20} → {escolhas[nome]}")
if escolhas["nenhum desvio"] != lab.MODELO_FLASH:
    falhar("contrato sem nenhum desvio foi para o Pro: a cascata não economiza nada assim. Confira o if.")
if escolhas["4 desvios"] != lab.MODELO_PRO:
    falhar("contrato com os 4 desvios ficou no Flash: o caso mais arriscado precisa do Pro. Confira o if.")
print("✓ regra coerente: contrato limpo fica no Flash, o mais arriscado vai para o Pro")

# 2. Dois contratos reais
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    falhar("GOOGLE_CLOUD_PROJECT não definido: rode `lab 05` para criar o .env com o seu projeto GCP.")


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
        resultados[nome] = rodar(auditar((LAB_DIR / arquivo).read_text(encoding="utf-8")))
    except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
        falhar(f"a chamada ao Gemini falhou: {erro}")

print("-" * 72)
print(f"{'Contrato':10} {'Desvios':>7}  {'Modelo que respondeu':24} {'Tempo':>7} {'Tokens':>7}")
for nome, r in resultados.items():
    print(f"{nome:10} {r['desvios']:>7}  {r['modelo_real']:24} {r['tempo']:6.1f}s {r['tokens']:>7}")
print("-" * 72)
for nome, r in resultados.items():
    print(f"{nome}: {r['parecer'].strip().splitlines()[0]}")
    if r.get("motivo_modelo"):
        print(f"  motivo registrado: {r['motivo_modelo']}")
print("-" * 72)

if not resultados["TechNova"]["modelo_real"].startswith(lab.MODELO_PRO):
    falhar("o contrato TechNova tem desvios e deveria ter ido para o Pro.")
if not resultados["VeloNet"]["modelo_real"].startswith(lab.MODELO_FLASH):
    falhar(f"o contrato VeloNet veio com {resultados['VeloNet']['desvios']} desvio(s) e foi para o Pro. "
           "Rode de novo: o compliance às vezes é rigoroso demais.")
print("✓ o Pro só entrou onde havia risco. Lab 05 concluído!")
