"""Lab 03 (solução): um assistente que responde perguntas buscando nas páginas do contrato."""

import os

from google.adk.agents import Agent

from .busca import buscar


def buscar_no_contrato(consulta: str) -> dict:
    """Busca no contrato da TechNova os trechos que tratam de um assunto.

    Use antes de responder qualquer pergunta sobre o contrato. Cada trecho volta com a página
    onde está, para ser citada na resposta.

    Args:
        consulta: palavras-chave do assunto procurado, ex.: "foro legislação" ou "multa rescisão".
    """
    trechos = buscar(consulta, quantidade=3)
    return {"trechos": [{"pagina": t.pagina, "texto": t.texto} for t in trechos]}


root_agent = Agent(
    name="assistente_contrato",
    model=os.getenv("MODELO_GEMINI", "gemini-3.8-flash"),
    description="Responde perguntas sobre o contrato da TechNova citando a página de cada informação.",
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
    # O Gemini decide sozinho quando chamar a ferramenta e com qual consulta
    tools=[buscar_no_contrato],
)
