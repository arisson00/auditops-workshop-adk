"""Lab 02 (solução): o extrator devolve um JSON com campos fixos, em vez de texto livre."""

import os

from google.adk.agents import Agent

from .schemas import ExtracaoContrato

root_agent = Agent(
    name="extrator_contratos",
    model=os.getenv("MODELO_GEMINI", "gemini-3.8-flash"),
    description="Extrai partes, valor, prazo, foro e cláusulas de risco de um contrato, com a página de cada uma.",
    instruction="""
Você é um analista de contratos de uma área de Compras. O usuário vai colar o texto de um contrato,
dividido em páginas marcadas assim: --- [Página X] ---

Extraia os dados pedidos no formato de resposta. Regras:
- Use somente o que está escrito no contrato. O que não aparece fica null.
- A página de cada cláusula é a do marcador --- [Página X] --- logo acima dela.
- Avalie o risco sempre do ponto de vista da CONTRATANTE.
""",
    # O Gemini passa a responder obrigatoriamente com um JSON neste formato
    output_schema=ExtracaoContrato,
    # A resposta fica guardada no estado da sessão com esta chave, para outros agentes usarem
    output_key="extracao",
)
