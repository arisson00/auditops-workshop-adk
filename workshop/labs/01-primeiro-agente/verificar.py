"""Confere o Lab 01. Rode de dentro de starter/ (ou solucao/):  python ../verificar.py

1. Confere se os TODOs foram preenchidos.
2. Manda o contrato de exemplo para o agente e confere se a resposta cita as páginas.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, os.getcwd())
load_dotenv(Path.cwd() / "resumidor" / ".env")


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


try:
    from resumidor.agent import root_agent
except ModuleNotFoundError:
    falhar("não achei a pasta resumidor/. Rode este script de dentro de starter/ ou solucao/.")

# 1. TODOs
if "TODO" in str(root_agent.model):
    falhar("TODO 1 pendente: defina o modelo (ex.: gemini-3.8-flash).")
if "TODO" in root_agent.description:
    falhar("TODO 2 pendente: escreva a descrição do agente.")
if "TODO" in root_agent.instruction or len(root_agent.instruction.strip()) < 80:
    falhar("TODO 3 pendente: escreva as instruções do agente.")
if "página" not in root_agent.instruction.lower():
    falhar("as instruções não falam em página: peça que o agente cite a página de cada ponto.")
print(f"✓ agente {root_agent.name} configurado com {root_agent.model}")

# 2. Chamada real ao Gemini
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    falhar("GOOGLE_CLOUD_PROJECT não definido: crie o arquivo resumidor/.env (passo 2 do README).")


async def perguntar(texto: str) -> str:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=root_agent, app_name="lab01")
    session = await runner.session_service.create_session(app_name="lab01", user_id="aluno")
    resposta = ""
    async for event in runner.run_async(
        user_id="aluno",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=texto)]),
    ):
        if event.content and event.content.parts:
            resposta += "".join(p.text or "" for p in event.content.parts)
    return resposta


print("… enviando contrato_exemplo.md ao Gemini")
try:
    resposta = asyncio.run(perguntar((LAB_DIR / "contrato_exemplo.md").read_text(encoding="utf-8")))
except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
    falhar(f"a chamada ao Gemini falhou: {erro}")

print("-" * 60)
print(resposta.strip())
print("-" * 60)

paginas = set(re.findall(r"P[áa]gina\s+(\d)", resposta))
if len(paginas) < 2:
    falhar("a resposta deveria citar pelo menos 2 páginas diferentes. Reforce isso nas instruções.")
print(f"✓ a resposta cita as páginas {', '.join(sorted(paginas))}. Lab 01 concluído!")
