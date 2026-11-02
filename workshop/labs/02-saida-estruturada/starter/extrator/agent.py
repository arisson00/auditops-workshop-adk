"""Lab 02: o extrator devolve um JSON com campos fixos, em vez de texto livre.

O agente já está pronto. Rode `python ../verificar.py` a partir desta pasta (starter/) para testá-lo.
Depois, se quiser, acrescente campos no schemas.py e rode de novo.
"""

import os

from google.adk.agents import Agent

from .schemas import ExtracaoContrato

root_agent = Agent(
    name="extrator_contratos",
    model=os.getenv("MODELO_GEMINI", "gemini-3.8-flash"),
    description="Extrai partes, valor, prazo, foro e cláusulas de risco de um contrato, com a página de cada uma.",
    # As instruções ficaram curtas: o QUE extrair está no schema, campo a campo
    instruction="""
Você é um analista de contratos de uma área de Compras. O usuário vai colar o texto de um contrato,
dividido em páginas marcadas assim: --- [Página X] ---

Extraia os dados pedidos no formato de resposta. Regras:
- Use somente o que está escrito no contrato. O que não aparece fica null.
- A página de cada cláusula é a do marcador --- [Página X] --- logo acima dela.
- Avalie o risco sempre do ponto de vista da CONTRATANTE.
""",
    # NOVO NESTE LAB: o Gemini passa a responder obrigatoriamente com um JSON no formato ExtracaoContrato
    output_schema=ExtracaoContrato,
    # NOVO NESTE LAB: a resposta fica guardada no estado da sessão com esta chave, para outros agentes usarem
    output_key="extracao",
)
