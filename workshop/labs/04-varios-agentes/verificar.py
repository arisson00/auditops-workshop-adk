"""Confere o Lab 04. Rode de dentro de starter/ (ou solucao/):  python ../verificar.py

1. Confere se a equipe de agentes está montada.
2. Manda o contrato da TechNova, mostra a linha do tempo de cada agente e o parecer final.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, os.getcwd())
load_dotenv(Path.cwd() / "auditoria" / ".env")


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


try:
    from google.adk.agents import ParallelAgent, SequentialAgent

    from auditoria import agent as equipe
except ModuleNotFoundError:
    falhar("não achei a pasta auditoria/. Rode este script de dentro de starter/ ou solucao/.")

# 1. TODOs
if equipe.compliance.output_key != "compliance" or equipe.risco.output_key != "risco":
    falhar('TODO 1 pendente: compliance e risco precisam de output_key "compliance" e "risco".')
analise = getattr(equipe, "analise", None)
if not isinstance(analise, ParallelAgent) or sorted(a.name for a in analise.sub_agents) != ["compliance", "risco"]:
    falhar("TODO 2 pendente: monte `analise` como ParallelAgent com compliance e risco.")
instrucao_parecer = equipe.parecer.instruction
if "TODO" in instrucao_parecer or "{compliance}" not in instrucao_parecer or "{risco}" not in instrucao_parecer:
    falhar("TODO 3 pendente: as instruções do parecer precisam ler {compliance} e {risco}.")
raiz = equipe.root_agent
if not isinstance(raiz, SequentialAgent) or raiz.sub_agents != [equipe.extrator, analise, equipe.parecer]:
    falhar("TODO 4 pendente: root_agent deve ser um SequentialAgent com [extrator, analise, parecer].")
print("✓ equipe montada: extrator → (compliance ∥ risco) → parecer")

# 2. Auditoria real
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    falhar("GOOGLE_CLOUD_PROJECT não definido: crie o arquivo auditoria/.env (passo 1 do README).")


async def auditar(texto: str) -> dict:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=raiz, app_name="lab04")
    session = await runner.session_service.create_session(app_name="lab04", user_id="aluno")
    inicio, vistos = time.monotonic(), set()
    print("\nLinha do tempo (segundos desde o início):")
    async for event in runner.run_async(
        user_id="aluno",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=texto)]),
    ):
        if event.author not in vistos and event.author != "user":
            vistos.add(event.author)
            print(f"  {time.monotonic() - inicio:5.1f}s  {event.author} terminou")
    session = await runner.session_service.get_session(app_name="lab04", user_id="aluno", session_id=session.id)
    return session.state


print("… enviando contrato_technova.md à equipe (leva de 30 a 60 segundos)")
try:
    estado = asyncio.run(auditar((LAB_DIR / "contrato_technova.md").read_text(encoding="utf-8")))
except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
    falhar(f"a chamada ao Gemini falhou: {erro}")

faltando = [k for k in ("extracao", "compliance", "risco", "parecer") if not estado.get(k)]
if faltando:
    falhar(f"o estado da sessão ficou sem: {', '.join(faltando)}. Confira os output_key.")
print(f"\n✓ estado da sessão: {', '.join(k for k in estado if not k.startswith('_'))}")

print("-" * 60)
print(estado["parecer"].strip())
print("-" * 60)

if "NÃO CONFORME" not in estado["compliance"].upper():
    falhar("o compliance deveria reprovar alguma política (o contrato TechNova tem várias violações).")
if "NÃO ASSINAR" not in estado["parecer"].upper() and "AJUSTES" not in estado["parecer"].upper():
    falhar("o parecer deveria recomendar não assinar ou assinar com ajustes.")
print("✓ a equipe auditou o contrato e chegou a um parecer. Lab 04 concluído!")
