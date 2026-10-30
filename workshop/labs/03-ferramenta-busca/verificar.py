"""Confere o Lab 03. Rode de dentro de starter/ (ou solucao/):  python ../verificar.py

1. Confere se os TODOs foram preenchidos e se a ferramenta devolve os trechos certos.
2. Faz 3 perguntas ao agente e mostra cada chamada que ele fez à ferramenta.
"""

import asyncio
import os
import re
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Aviso interno do ADK ao montar a declaração da ferramenta; não afeta o lab
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]")
sys.path.insert(0, os.getcwd())
load_dotenv(Path.cwd() / "assistente" / ".env")


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


try:
    from assistente.agent import buscar_no_contrato, root_agent
except ModuleNotFoundError:
    falhar("não achei a pasta assistente/. Rode este script de dentro de starter/ ou solucao/.")

# 1. TODOs
docstring = buscar_no_contrato.__doc__ or ""
if "TODO" in docstring or len(docstring.strip()) < 40:
    falhar("TODO 1 pendente: escreva a docstring da ferramenta buscar_no_contrato.")
retorno = buscar_no_contrato("foro")
trechos = retorno.get("trechos") if isinstance(retorno, dict) else None
if not trechos:
    falhar('TODO 2 pendente: a ferramenta deve devolver {"trechos": [{"pagina": ..., "texto": ...}]}.')
if trechos[0].get("pagina") != 5 or "Delaware" not in trechos[0].get("texto", ""):
    falhar('TODO 2: buscar_no_contrato("foro") deveria trazer a Cláusula 14, na página 5.')
if buscar_no_contrato not in root_agent.tools:
    falhar("TODO 3 pendente: passe tools=[buscar_no_contrato] para o Agent.")
if "TODO" in root_agent.instruction:
    falhar("TODO 4 pendente: escreva as regras nas instruções do agente.")
if "não consta no contrato" not in root_agent.instruction.lower():
    falhar('TODO 4: as regras precisam dizer para responder "Não consta no contrato." quando não achar.')
print(f"✓ ferramenta pronta e entregue ao agente {root_agent.name}")

# 2. Perguntas reais ao Gemini
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    falhar("GOOGLE_CLOUD_PROJECT não definido: crie o arquivo assistente/.env (passo 1 do README).")


async def perguntar(pergunta: str) -> tuple[str, list[str]]:
    """Faz uma pergunta numa sessão nova e devolve a resposta e as consultas que o agente fez."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=root_agent, app_name="lab03")
    session = await runner.session_service.create_session(app_name="lab03", user_id="aluno")
    resposta, consultas = "", []
    async for event in runner.run_async(
        user_id="aluno",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=pergunta)]),
    ):
        for chamada in event.get_function_calls():
            consultas.append(chamada.args.get("consulta", ""))
        if event.is_final_response() and event.content and event.content.parts:
            resposta += "".join(p.text or "" for p in event.content.parts)
    return resposta.strip(), consultas


# Cada caso: pergunta, página que a resposta precisa citar (None = não está no contrato), palavra esperada
CASOS = [
    ("Qual é o foro deste contrato?", "5", r"Delaware|Nova York"),
    ("Podemos cancelar o contrato antes do prazo? Quanto custa?", "4", r"50\s?%"),
    ("Qual é o telefone do suporte técnico?", None, r"[Nn]ão consta no contrato"),
]

for pergunta, pagina, esperado in CASOS:
    print(f"\n? {pergunta}")
    try:
        resposta, consultas = asyncio.run(perguntar(pergunta))
    except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
        falhar(f"a chamada ao Gemini falhou: {erro}")
    for consulta in consultas:
        print(f'  → buscar_no_contrato(consulta="{consulta}")')
    print(f"  {resposta}")
    if not consultas:
        falhar("o agente respondeu sem usar a ferramenta. Reforce nas regras que ele deve buscar antes.")
    if not re.search(esperado, resposta):
        falhar(f"a resposta deveria conter {esperado!r}.")
    if pagina and not re.search(rf"P[áa]gina\s+{pagina}", resposta):
        falhar(f"a resposta deveria citar a Página {pagina}.")

print("\n✓ o agente buscou antes de responder, citou as páginas e não inventou. Lab 03 concluído!")
