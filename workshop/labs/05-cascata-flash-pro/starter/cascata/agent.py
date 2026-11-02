"""Lab 05: o parecer usa o Gemini Pro só quando o compliance encontra desvio.

    compliance (Flash) ──► escolher_modelo() ──► parecer (Flash ou Pro)

A escolha do modelo é uma regra de negócio em Python, não uma decisão do modelo: é previsível,
fácil de auditar e de explicar para a área de Compras.

O agente já está pronto. Rode `python ../verificar.py` a partir desta pasta (starter/) para testá-lo.
Depois, se quiser, mude a regra: veja "PERSONALIZE" na função escolher_modelo.
"""

import os
from pathlib import Path
from typing import Literal

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
from pydantic import BaseModel, Field

MODELO_FLASH = os.getenv("MODELO_FLASH", "gemini-3.8-flash")
MODELO_PRO = os.getenv("MODELO_PRO", "gemini-3.1-pro-preview")
POLITICAS = (Path(__file__).resolve().parents[2] / "politicas_compliance.md").read_text(encoding="utf-8")


class AvaliacaoPolitica(BaseModel):
    politica: str = Field(description="Código da política, ex.: POL-LGPD-01")
    status: Literal["CONFORME", "NAO_CONFORME"]
    motivo: str = Field(description="Por que, em uma frase")
    pagina: int | None = Field(description="Página do contrato que motivou a avaliação")


class Conformidade(BaseModel):
    politicas: list[AvaliacaoPolitica] = Field(description="Uma avaliação para cada política")


# 1. Compliance no Flash, com saída estruturada (Lab 02): a regra abaixo precisa ler campos, não texto
compliance = Agent(
    name="compliance",
    model=MODELO_FLASH,
    description="Confere o contrato contra as políticas internas de compliance.",
    instruction="""
O usuário colou um contrato dividido em páginas (--- [Página X] ---). Avalie o contrato contra cada
uma das 4 políticas abaixo (POL-LGPD-01, POL-SLA-02, POL-FIN-03, POL-JUR-04).

""" + POLITICAS,
    output_schema=Conformidade,
    output_key="compliance",
)


# NOVO NESTE LAB: um callback, função que o ADK chama logo antes de cada chamada ao Gemini
def escolher_modelo(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    """Roda logo antes de o parecer chamar o Gemini e troca o modelo quando há desvio."""
    # A avaliação do compliance, gravada no estado pelo output_key (um dicionário, graças ao schema)
    conformidade = callback_context.state.get("compliance") or {}
    # As políticas reprovadas. Cada item tem "politica" (ex.: POL-JUR-04), "status", "motivo" e "pagina"
    desvios = [p for p in conformidade.get("politicas", []) if p["status"] == "NAO_CONFORME"]
    # PERSONALIZE AQUI: troque a condição do if para mudar quando o Pro entra. Exemplos:
    #   if len(desvios) >= 2:                                      só com 2 ou mais desvios
    #   if any(p["politica"] == "POL-JUR-04" for p in desvios):    só com desvio jurídico
    if desvios:
        # Troca o modelo só desta chamada: o agente continua sendo criado com o Flash
        llm_request.model = MODELO_PRO
    # Fica registrado no estado: a interface e os relatórios de custo mostram qual modelo decidiu
    callback_context.state["desvios"] = len(desvios)
    callback_context.state["modelo_parecer"] = llm_request.model
    # PERSONALIZE: registre também o motivo da escolha (o verificar.py mostra este texto)
    # callback_context.state["motivo_modelo"] = f"{len(desvios)} desvio(s): " + ", ".join(p["politica"] for p in desvios)
    return None  # None = segue com a chamada; devolver uma resposta pularia o Gemini


# 2. Parecer: nasce no Flash; o callback promove para o Pro quando precisa
parecer = Agent(
    name="parecer",
    model=MODELO_FLASH,
    description="Escreve o parecer final para a diretoria.",
    instruction="""
Você escreve para a diretoria. Com base na avaliação de compliance abaixo, escreva:

**Recomendação:** ASSINAR, ASSINAR COM AJUSTES ou NÃO ASSINAR SEM AJUSTES, e o motivo em uma frase.
**O que negociar:** os ajustes necessários, cada um com a página. Se não houver, diga "nenhum".

Avaliação de compliance:
{compliance}
""",
    # NOVO NESTE LAB: a regra roda antes de cada chamada do parecer ao Gemini
    before_model_callback=escolher_modelo,
    output_key="parecer",
)

root_agent = SequentialAgent(
    name="cascata",
    description="Audita um contrato e escala o parecer para o Gemini Pro só quando há risco.",
    sub_agents=[compliance, parecer],
)
