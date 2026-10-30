"""Lab 02: o extrator devolve um JSON com campos fixos, em vez de texto livre.

Preencha os TODOs deste arquivo e do schemas.py e rode `python ../verificar.py` a partir de starter/.
"""

import os

from google.adk.agents import Agent

from .schemas import ExtracaoContrato  # noqa: F401 - você vai usar no TODO 3

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
    # TODO 3: obrigue o Gemini a responder no formato ExtracaoContrato.
    #         Dica: o parâmetro se chama output_schema
    # TODO 4: guarde a resposta no estado da sessão com a chave "extracao".
    #         Dica: o parâmetro se chama output_key
)
