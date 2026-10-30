"""Lab 01: um agente que lê um contrato e devolve um resumo executivo com as páginas.

Preencha os três TODOs abaixo e rode `python ../verificar.py` a partir desta pasta (starter/).
"""

import os

from google.adk.agents import Agent

root_agent = Agent(
    name="resumidor_contratos",
    # TODO 1: escolha o modelo. Use o Gemini Flash: "gemini-3.8-flash"
    model=os.getenv("MODELO_GEMINI", "TODO"),
    # TODO 2: descreva em uma frase o que este agente faz.
    #         Em um sistema com vários agentes, é essa descrição que os outros agentes leem.
    description="TODO",
    # TODO 3: escreva as instruções do agente (o "prompt de sistema"). Elas precisam:
    #   a) dizer que o usuário vai colar um contrato dividido em páginas: --- [Página X] ---
    #   b) pedir um resumo com partes, objeto, valor e prazo
    #   c) pedir até 3 pontos de atenção, cada um citando a página, ex.: (Página 2)
    #   d) proibir inventar: o que não está no contrato vira "não informado"
    instruction="""
TODO
""",
)
