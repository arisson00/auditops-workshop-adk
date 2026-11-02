"""Lab 04: uma equipe de agentes especialistas audita um contrato.

    extrator ──► ┌ compliance ┐ ──► parecer
                 │ risco      │
                 └ (o seu)    ┘
    (Sequential: um depois do outro; no meio, Parallel: os especialistas ao mesmo tempo)

Cada agente grava a resposta no estado da sessão (output_key), e o próximo lê com {chave}
nas instruções.

A equipe já está pronta. Rode `python ../verificar.py` a partir desta pasta (starter/) para testá-la.
Depois, monte o seu especialista: veja "MONTE O SEU ESPECIALISTA" mais abaixo.
"""

import os
from pathlib import Path

from google.adk.agents import Agent, ParallelAgent, SequentialAgent

MODELO = os.getenv("MODELO_GEMINI", "gemini-3.8-flash")
POLITICAS = (Path(__file__).resolve().parents[2] / "politicas_compliance.md").read_text(encoding="utf-8")

# 1. Extrator: lê o contrato que o usuário colou e anota os pontos principais com a página
extrator = Agent(
    name="extrator",
    model=MODELO,
    description="Lista as cláusulas principais do contrato com a página de cada uma.",
    instruction="""
O usuário colou um contrato dividido em páginas (--- [Página X] ---). Liste, em tópicos curtos,
partes, valor, prazo e renovação, SLA, dados pessoais, multa de rescisão, responsabilidade e foro.
Cada tópico termina com a página, ex.: (Página 3). Não opine: só extraia.
""",
    # Grava a resposta no estado da sessão; os especialistas leem com {extracao}
    output_key="extracao",
)

# 2a. Especialista em compliance: confere a extração contra as políticas internas
compliance = Agent(
    name="compliance",
    model=MODELO,
    description="Confere o contrato contra as políticas internas de compliance.",
    instruction="""
Você é o analista de compliance. Compare as cláusulas extraídas com as políticas da empresa.

Cláusulas extraídas do contrato:
{extracao}

Políticas da empresa:
""" + POLITICAS + """

Para cada política (POL-LGPD-01, POL-SLA-02, POL-FIN-03, POL-JUR-04), responda em uma linha:
código da política, CONFORME ou NÃO CONFORME, e o motivo citando a página do contrato.
""",
    output_key="compliance",
)

# 2b. Especialista em risco jurídico: olha a mesma extração com os olhos de um advogado
risco = Agent(
    name="risco",
    model=MODELO,
    description="Avalia o risco jurídico e financeiro das cláusulas para a contratante.",
    instruction="""
Você é o advogado da contratante. Com base nas cláusulas extraídas abaixo, aponte os 3 maiores
riscos jurídicos ou financeiros para a contratante, do mais grave para o menos grave.
Para cada um: o risco em uma frase, a página e uma sugestão de redação alternativa.

Cláusulas extraídas do contrato:
{extracao}
""",
    output_key="risco",
)

# ─── MONTE O SEU ESPECIALISTA ──────────────────────────────────────────────────────────
# 1. Tire o "# " do começo das linhas do bloco abaixo (ou cole outro especialista do README).
# 2. Acrescente o nome dele na lista ESPECIALISTAS, logo depois do bloco.
# Pronto: ele roda em paralelo com os outros e o parecer passa a ler a análise dele.
#
# financeiro = Agent(
#     name="financeiro",
#     model=MODELO,
#     description="Avalia o impacto financeiro do contrato para a contratante.",
#     instruction="""
# Você é o analista financeiro da contratante. Com base nas cláusulas extraídas abaixo, calcule
# o custo total do contrato no prazo de vigência e aponte os 3 maiores riscos financeiros
# (reajuste, multas, custos escondidos), cada um com a página.
#
# Cláusulas extraídas do contrato:
# {extracao}
# """,
#     output_key="financeiro",
# )
# ───────────────────────────────────────────────────────────────────────────────────────

# A lista de especialistas. Todos rodam ao mesmo tempo: nenhum depende do resultado do outro
ESPECIALISTAS = [compliance, risco]  # ex.: [compliance, risco, financeiro]

analise = ParallelAgent(
    name="analise_paralela",
    sub_agents=ESPECIALISTAS,
)

# O parecer lê a análise de cada especialista da lista: "{compliance}", "{risco}" e a do seu.
# Montamos esse trecho a partir da lista, então um especialista novo entra sozinho no parecer
ANALISES = "\n\n".join(f"Análise de {e.name}:\n{{{e.output_key}}}" for e in ESPECIALISTAS)

# 3. Parecer: junta as análises numa recomendação para a diretoria
parecer = Agent(
    name="parecer",
    model=MODELO,
    description="Escreve o parecer final para a diretoria.",
    instruction="""
Você escreve para a diretoria, que tem 1 minuto para ler. Com base nas análises dos especialistas
abaixo, escreva:

**Recomendação:** ASSINAR, ASSINAR COM AJUSTES ou NÃO ASSINAR SEM AJUSTES, e o motivo em uma frase.
**O que negociar:** os 3 ajustes mais importantes, cada um com a página.

""" + ANALISES,
    output_key="parecer",
)

# A equipe: extrator, depois os especialistas em paralelo, depois o parecer
root_agent = SequentialAgent(
    name="auditoria",
    description="Audita um contrato com uma equipe de agentes especialistas.",
    sub_agents=[extrator, analise, parecer],
)
