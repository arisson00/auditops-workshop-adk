"""Confere o Lab 02. Rode de dentro de starter/ (ou solucao/):  python ../verificar.py

1. Confere se os TODOs foram preenchidos.
2. Manda o contrato de exemplo ao agente, lê o JSON guardado no estado da sessão e confere os campos.
3. Mostra por que o JSON importa: o resultado vira dados que o código consegue usar.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, os.getcwd())
load_dotenv(Path.cwd() / "extrator" / ".env")


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


try:
    from extrator.agent import root_agent
    from extrator.schemas import Clausula, ExtracaoContrato
except ModuleNotFoundError:
    falhar("não achei a pasta extrator/. Rode este script de dentro de starter/ ou solucao/.")

# 1. TODOs
campos = Clausula.model_fields
if "pagina" not in campos:
    falhar("TODO 1 pendente: adicione o campo `pagina` na classe Clausula (schemas.py).")
if campos["pagina"].annotation is not int:
    falhar("TODO 1: o campo `pagina` precisa ser do tipo int.")
if "risco" not in campos:
    falhar("TODO 2 pendente: adicione o campo `risco` na classe Clausula (schemas.py).")
if getattr(campos["risco"].annotation, "__args__", None) != ("alto", "medio", "baixo"):
    falhar('TODO 2: o tipo de `risco` deve ser Literal["alto", "medio", "baixo"].')
if root_agent.output_schema is not ExtracaoContrato:
    falhar("TODO 3 pendente: passe output_schema=ExtracaoContrato para o Agent (agent.py).")
if root_agent.output_key != "extracao":
    falhar('TODO 4 pendente: passe output_key="extracao" para o Agent (agent.py).')
print(f"✓ agente {root_agent.name} responde no formato ExtracaoContrato")

# 2. Chamada real ao Gemini
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    falhar("GOOGLE_CLOUD_PROJECT não definido: crie o arquivo extrator/.env (passo 2 do README).")


async def extrair(texto: str) -> dict:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=root_agent, app_name="lab02")
    session = await runner.session_service.create_session(app_name="lab02", user_id="aluno")
    async for _ in runner.run_async(
        user_id="aluno",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=texto)]),
    ):
        pass
    # Com output_key, a resposta fica no estado da sessão: é assim que outros agentes vão lê-la
    session = await runner.session_service.get_session(app_name="lab02", user_id="aluno", session_id=session.id)
    return session.state.get("extracao")


print("… enviando contrato_exemplo.md ao Gemini")
try:
    estado = asyncio.run(extrair((LAB_DIR / "contrato_exemplo.md").read_text(encoding="utf-8")))
except Exception as erro:  # noqa: BLE001 - mostrar o motivo ao participante é o objetivo aqui
    falhar(f"a chamada ao Gemini falhou: {erro}")

if not estado:
    falhar('nada foi salvo em state["extracao"]. Confira o output_key.')
extracao = ExtracaoContrato.model_validate(estado)
print('✓ o JSON foi salvo em state["extracao"] e passou na validação do schema')

# Conferências com o gabarito do contrato de exemplo
if extracao.prazo_meses != 24:
    falhar(f"prazo_meses deveria ser 24, veio {extracao.prazo_meses}.")
if not extracao.renovacao_automatica:
    falhar("renovacao_automatica deveria ser true (Cláusula 3.2).")
if not extracao.foro or "São Paulo" not in extracao.foro:
    falhar(f"o foro deveria ser São Paulo, veio {extracao.foro}.")
if len(extracao.clausulas) < 3:
    falhar(f"esperava pelo menos 3 cláusulas de atenção, vieram {len(extracao.clausulas)}.")
if any(c.pagina not in (1, 2, 3) for c in extracao.clausulas):
    falhar("alguma cláusula veio com página fora de 1 a 3: o contrato só tem 3 páginas.")

# 3. Com JSON, o resultado vira dados: filtrar, ordenar e contar é só Python
print("-" * 60)
print(f"Partes : {' × '.join(extracao.partes)}")
print(f"Valor  : {extracao.valor_mensal} por mês, {extracao.prazo_meses} meses, foro {extracao.foro}")
print("Cláusulas, da mais arriscada para a menos:")
ordem = {"alto": 0, "medio": 1, "baixo": 2}
for c in sorted(extracao.clausulas, key=lambda c: (ordem[c.risco], c.pagina)):
    print(f"  [{c.risco:5}] p.{c.pagina}  {c.titulo}")
altos = sum(c.risco == "alto" for c in extracao.clausulas)
print("-" * 60)
print(f"✓ {altos} cláusula(s) de risco alto. Lab 02 concluído!")
