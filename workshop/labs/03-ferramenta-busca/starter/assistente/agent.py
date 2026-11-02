"""Lab 03: um assistente que responde perguntas buscando nas páginas do contrato.

O agente já está pronto. Rode `python ../verificar.py` a partir desta pasta (starter/) para testá-lo,
ou `python ../verificar.py "sua pergunta"` para perguntar o que quiser.
"""

import os

from google.adk.agents import Agent

from .busca import buscar


# Uma ferramenta é uma função Python comum. O ADK mostra ao Gemini o nome, os argumentos e a
# docstring (o texto entre """ logo abaixo), e o Gemini decide sozinho quando chamá-la e com o quê
def buscar_no_contrato(consulta: str) -> dict:
    """Busca no contrato da TechNova os trechos que tratam de um assunto.

    Use antes de responder qualquer pergunta sobre o contrato. Cada trecho volta com a página
    onde está, para ser citada na resposta.

    Args:
        consulta: palavras-chave do assunto procurado, ex.: "foro legislação" ou "multa rescisão".
    """
    # PERSONALIZE: mude a quantidade de trechos (1, 3, 5...) e veja se as respostas melhoram ou pioram
    trechos = buscar(consulta, quantidade=3)
    # O que a função devolve é o que o Gemini lê: aqui, os trechos com a página de cada um
    return {"trechos": [{"pagina": t.pagina, "texto": t.texto} for t in trechos]}


root_agent = Agent(
    name="assistente_contrato",
    model=os.getenv("MODELO_GEMINI", "gemini-3.8-flash"),
    description="Responde perguntas sobre o contrato da TechNova citando a página de cada informação.",
    # PERSONALIZE AQUI: mude as regras e veja como o agente passa a usar a ferramenta.
    # Mantenha a última regra igual: o verificar.py confere a frase "Não consta no contrato."
    instruction="""
Você é o assistente de contratos da área de Compras. Você responde perguntas sobre o contrato de
prestação de serviços SaaS da TechNova Soluções Digitais com a Global Retail Corp Brasil.

Regras:
- Antes de responder, use a ferramenta buscar_no_contrato. Se a primeira busca não trouxer o
  assunto, tente de novo com outras palavras-chave (sinônimos).
- Responda só com base nos trechos que a ferramenta devolveu, em no máximo 4 frases,
  e cite a página de cada informação, ex.: (Página 5).
- Se depois das buscas o assunto não aparecer, responda exatamente: "Não consta no contrato."
""",
    # NOVO NESTE LAB: a lista de ferramentas que o agente pode usar
    tools=[buscar_no_contrato],
)
