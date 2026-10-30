"""Schemas Pydantic para troca de dados estruturada entre os agentes do AuditOps 2.0.

Inclui suporte completo a:
- Rastreabilidade de Página e Cláusula (`contract_page`, `rag_source_citation`)
- Chunks recuperados do Banco Vetorial (`RagRetrievedChunk`)
- Agente Assistente de Insights (`AssistantInsights`, `NegotiationLeverage`)
- Métricas de Escalonamento (Flash -> 3.1 Pro) e FinOps
"""

from typing import List, Optional, Literal, Dict, Any
import json

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    class BaseModel:
        """Fallback leve compatível com a API básica do Pydantic v2 BaseModel."""
        def __init__(self, **kwargs):
            for k, val in self.__class__.__dict__.items():
                if not k.startswith("_") and not callable(val):
                    setattr(self, k, val() if callable(val) else val)
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            res = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                else:
                    res[k] = v
            return res

        def model_dump_json(self, indent: Optional[int] = None) -> str:
            return json.dumps(self.model_dump(), default=str, indent=indent, ensure_ascii=False)

        @classmethod
        def model_validate_json(cls, json_str: str) -> "BaseModel":
            data = json.loads(json_str)
            return cls(**data)

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}({self.__dict__})"

    def Field(default=None, default_factory=None, description=None, ge=None, le=None):
        if default_factory is not None:
            return default_factory
        return default


class ClauseLocation(BaseModel):
    """Mapeamento de cláusula extraída com a página exata onde se encontra no contrato."""
    clause_summary: str = Field(default="", description="Resumo da cláusula e seu impacto")
    contract_page: int = Field(default=1, description="Número da página do contrato onde a cláusula está localizada")
    clause_id: str = Field(default="", description="Identificador da cláusula (ex: Cláusula 4.1)")


class ContractMetadata(BaseModel):
    """Metadados extraídos na Triagem Inicial (Camada Flash)."""
    title: str = Field(default="", description="Título ou identificador do contrato")
    parties: List[str] = Field(default_factory=list, description="Partes contratantes identificadas")
    effective_date: Optional[str] = Field(default=None, description="Data de início ou vigência")
    duration: Optional[str] = Field(default=None, description="Prazo de vigência contratual")
    contract_value: Optional[str] = Field(default=None, description="Valor global ou mensal do contrato")
    value_page: int = Field(default=1, description="Página do contrato onde consta o valor financeiro")
    jurisdiction: Optional[str] = Field(default=None, description="Foro e legislação aplicável")
    jurisdiction_page: int = Field(default=1, description="Página do contrato onde consta a eleição de foro")
    main_objective: str = Field(default="", description="Objeto principal do contrato")
    key_clauses_extracted: List[str] = Field(
        default_factory=list,
        description="Lista de cláusulas relevantes detectadas com indicação de página"
    )
    clause_locations: List[ClauseLocation] = Field(
        default_factory=list,
        description="Mapeamento estruturado das cláusulas e suas respectivas páginas no contrato"
    )


class RagRetrievedChunk(BaseModel):
    """Evidência recuperada do Banco Vetorial (RAG) durante a auditoria."""
    chunk_id: str = Field(default="")
    source_document: str = Field(default="", description="Arquivo da base de conhecimento ou contrato")
    page_number: int = Field(default=1, description="Página de origem do documento")
    section_id: str = Field(default="", description="Código ou título da seção/cláusula")
    category: str = Field(default="GERAL")
    similarity_score: float = Field(default=0.92, description="Similaridade de cosseno (0 a 1)")
    citation_badge: str = Field(default="Pág. 1")
    text: str = Field(default="")


class ComplianceIssue(BaseModel):
    """Item de verificação de conformidade validado contra o Banco Vetorial (Camada Flash)."""
    category: Literal[
        "LGPD/Privacidade",
        "SLA/Disponibilidade",
        "Penalidades/Multas",
        "Propriedade Intelectual",
        "Responsabilidade Civil",
        "Foro/Jurisdição",
        "Rescisão"
    ] = Field(default="SLA/Disponibilidade", description="Categoria da política de compliance avaliada")
    status: Literal["CONFORME", "ALERTA", "NÃO CONFORME"] = Field(
        default="CONFORME",
        description="Status de adequação da cláusula"
    )
    contract_page: int = Field(
        default=1,
        description="Página exata do contrato de onde saiu a cláusula avaliada"
    )
    clause_reference: str = Field(
        default="",
        description="Número da cláusula e página no contrato (ex: Pág. 2 • Cláusula 4.1)"
    )
    evaluated_clause: str = Field(default="", description="Citação ou resumo da cláusula analisada")
    rag_policy_source: str = Field(
        default="",
        description="Documento e página da política no Banco Vetorial (ex: politicas_compliance_2026.md • Pág. 1 [POL-SLA-02])"
    )
    finding_details: str = Field(default="", description="Explicação objetiva da conformidade ou inconformidade")
    suggested_action: str = Field(default="", description="Ação corretiva recomendada")


class ComplianceCheckResult(BaseModel):
    """Resultado da checagem de conformidade padrão com RAG (Camada Flash)."""
    overall_status: str = Field(
        default="APROVADO",
        description="Parecer geral de conformidade (APROVADO, APROVADO COM RESSALVAS, REPROVADO)"
    )
    compliance_score: int = Field(
        default=100,
        description="Pontuação de conformidade de 0 a 100 baseada no playbook do banco vetorial"
    )
    requires_pro_escalation: bool = Field(
        default=False,
        description="Se True, aciona o escalonamento de regra de negócio para o modelo Gemini 3.1 Pro"
    )
    escalation_reasons: List[str] = Field(
        default_factory=list,
        description="Gatilhos de regra de negócio que motivaram o escalonamento para o 3.1 Pro"
    )
    issues: List[ComplianceIssue] = Field(
        default_factory=list,
        description="Lista detalhada dos pontos avaliados com página do contrato e fonte RAG"
    )


class HighRiskFinding(BaseModel):
    """Achado de risco crítico analisado pelo Jurídico Sênior (Tier 3 - Gemini 3.1 Pro)."""
    risk_category: str = Field(default="Responsabilidade Ilimitada", description="Tipo de risco jurídico detectado")
    severity: Literal["CRÍTICA", "ALTA", "MÉDIA"] = Field(default="ALTA", description="Gravidade do risco")
    contract_page: int = Field(
        default=1,
        description="Página exata do contrato onde está o trecho abusivo"
    )
    clause_id: str = Field(
        default="",
        description="Identificador da cláusula no contrato (ex: Cláusula 11.1)"
    )
    problematic_excerpt: str = Field(default="", description="Trecho problemático original do contrato")
    legal_analysis: str = Field(
        default="",
        description="Análise aprofundada de impacto financeiro ou exposição legal"
    )
    rag_redline_source: str = Field(
        default="",
        description="Fonte no banco vetorial da redline padrão (ex: manual_redlines_juridico.md • Pág. 1 [REDLINE-CAP-01])"
    )
    suggested_redline: str = Field(
        default="",
        description="Redação jurídica alternativa (minuta corretiva sugerida) para mitigar o risco"
    )


class LegalAuditReview(BaseModel):
    """Parecer Jurídico Sênior & Red Team (Executado pelo Gemini 3.1 Pro quando escalado)."""
    overall_risk_level: Literal["CRÍTICO", "ALTO", "MODERADO", "BAIXO"] = Field(
        default="MODERADO",
        description="Nível de risco consolidado do instrumento contratual"
    )
    escalated_to_pro: bool = Field(
        default=True,
        description="Indica se a análise profunda do 3.1 Pro foi necessária pelas regras de negócio"
    )
    executive_legal_opinion: str = Field(
        default="",
        description="Parecer executivo detalhado direcionado à diretoria"
    )
    high_risk_findings: List[HighRiskFinding] = Field(
        default_factory=list,
        description="Lista de cláusulas com armadilhas ou riscos severos identificados com página exata"
    )
    recommendation: str = Field(default="APROVAR INTEGRALMENTE", description="Recomendação de ação jurídica")


class NegotiationLeverage(BaseModel):
    """Alavanca estratégica de negociação gerada pelo Agente Assistente de Insights."""
    topic: str = Field(default="", description="Tópico de negociação (ex: Preço, SLA, Multa, Foro)")
    contract_page: int = Field(default=1, description="Página do contrato relacionada ao ponto de barganha")
    current_contract_term: str = Field(default="", description="O que o contrato pede hoje")
    historical_benchmark_rag: str = Field(
        default="",
        description="Precedente encontrado no Banco Vetorial (com fonte e página)"
    )
    recommended_tradeoff: str = Field(
        default="",
        description="Estratégia prática de ganha-ganha / trade-off para a mesa de negociação"
    )
    estimated_financial_impact: str = Field(
        default="",
        description=" Economia ou proteção financeira estimada (ex: R$ 32.400/ano de redução)"
    )


class ChatAnswer(BaseModel):
    """Resposta estruturada do Consultor de Contratos no chat (modo ADK real)."""
    answer: str = Field(default="", description="Resposta em markdown citando 'Página X' e as fontes do Banco Vetorial")
    referenced_pages: List[int] = Field(default_factory=list, description="Páginas do contrato citadas na resposta")


class AssistantInsights(BaseModel):
    """Output do Agente Assistente de Insights Executivos & Negociação."""
    assistant_summary: str = Field(
        default="",
        description="Síntese executiva em linguagem de negócios sobre o contrato"
    )
    financial_benchmark_status: str = Field(
        default="DENTRO DO BENCHMARK"
    )
    financial_insight_details: str = Field(
        default="",
        description="Análise comparativa do valor do contrato vs. base histórica no banco vetorial"
    )
    potential_annual_savings: str = Field(
        default="R$ 0,00",
        description="Economia anual potencial estimada em negociação (Procurement)"
    )
    negotiation_leverages: List[NegotiationLeverage] = Field(
        default_factory=list,
        description="Lista de alavancas de negociação com rastreabilidade de página"
    )
    suggested_questions: List[str] = Field(
        default_factory=list,
        description="Perguntas rápidas sugeridas para o usuário fazer ao Agente Assistente no Chat"
    )


class FinOpsMetrics(BaseModel):
    """Métricas de custo, latência e eficiência do roteamento por modelos (Flash -> 3.1 Pro)."""
    tier1_model: str = Field(default="gemini-3.8-flash")
    tier2_model: str = Field(default="gemini-3.8-flash")
    tier3_model: str = Field(default="gemini-3.1-pro-preview")
    pro_was_invoked: bool = Field(default=True, description="Indica se o Tier 3 (3.1 Pro) precisou ser acionado")
    tier1_latency_sec: float = Field(default=0.0)
    tier2_latency_sec: float = Field(default=0.0)
    tier3_latency_sec: float = Field(default=0.0)
    total_tokens_estimated: int = Field(default=0)
    estimated_cost_usd_routed: float = Field(default=0.0)
    estimated_cost_usd_all_pro: float = Field(default=0.0)
    estimated_cost_savings_pct: float = Field(default=0.0)


class AuditReport(BaseModel):
    """Relatório final consolidado gerado pelo orquestrador do AuditOps 2.0."""
    contract_title: str = Field(default="")
    metadata: ContractMetadata = Field(default_factory=ContractMetadata)
    compliance: ComplianceCheckResult = Field(default_factory=ComplianceCheckResult)
    legal_review: LegalAuditReview = Field(default_factory=LegalAuditReview)
    insights: AssistantInsights = Field(default_factory=AssistantInsights)
    rag_chunks_used: List[RagRetrievedChunk] = Field(default_factory=list)
    contract_pages_indexed: List[RagRetrievedChunk] = Field(default_factory=list)
    finops: FinOpsMetrics = Field(default_factory=FinOpsMetrics)
    execution_mode: str = Field(
        default="SIMULATED",
        description="Origem do relatório: LIVE_ADK (agentes ADK reais), SIMULATED (sem credenciais) ou SIMULATED_FALLBACK (falha no modo real)"
    )
    execution_detail: str = Field(default="", description="Motivo da simulação ou do fallback, exibido na UI")
