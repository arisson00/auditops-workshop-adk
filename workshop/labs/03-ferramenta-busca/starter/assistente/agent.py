"""Lab 03: um assistente que responde perguntas buscando nas páginas do contrato.

Preencha os TODOs e rode `python ../verificar.py` a partir de starter/.
"""

import os

from google.adk.agents import Agent

from .busca import buscar


def buscar_no_contrato(consulta: str) -> dict:
    """TODO 1: escreva aqui o que esta ferramenta faz e quando usá-la.

    O Gemini lê este texto (a docstring) para decidir quando chamar a ferramenta.
    Explique também o argumento `consulta`, com um exemplo, ex.: "foro legislação".
    """
    trechos = buscar(consulta, quantidade=3)
    # TODO 2: devolva um dicionário com os trechos, cada um com a página e o texto:
    #   return {"trechos": [{"pagina": t.pagina, "texto": t.texto} for t in trechos]}
    return {}


root_agent = Agent(
    name="assistente_contrato",
    model=os.getenv("MODELO_GEMINI", "gemini-3.8-flash"),
    description="Responde perguntas sobre o contrato da TechNova citando a página de cada informação.",
    instruction="""
Você é o assistente de contratos da área de Compras. Você responde perguntas sobre o contrato de
prestação de serviços SaaS da TechNova Soluções Digitais com a Global Retail Corp Brasil.

Regras:
TODO 4: escreva as regras do assistente. Elas precisam dizer:
  a) usar a ferramenta buscar_no_contrato antes de responder e, se não achar, tentar outras palavras
  b) responder só com base nos trechos devolvidos e citar a página, ex.: (Página 5)
  c) se o assunto não aparecer, responder exatamente: "Não consta no contrato."
""",
    # TODO 3: entregue a ferramenta ao agente. Dica: tools=[buscar_no_contrato]
)
