"""Ferramentas (Tools) especializadas para o AuditOps 2.0 com Agentic RAG e Rastreamento de Página.

Utilizadas pelos agentes ADK para:
1. Busca semântica no Banco Vetorial (`search_vector_knowledge_base`) retornando documento e página.
2. Localização exata de página e cláusula dentro do contrato analisado (`search_contract_pages`).
3. Busca de precedentes e benchmarks financeiros históricos (`search_historical_benchmarks`).
4. Cálculo matemático de índice de risco e métricas FinOps (Flash -> 3.1 Pro).
"""

from typing import Dict, Any, List
from audit_ops.rag_engine import GLOBAL_VECTOR_ENGINE


def search_vector_knowledge_base(query: str, category: str = "ALL") -> Dict[str, Any]:
    """Busca semântica no Banco Vetorial por políticas de compliance e modelos de redlines.

    Args:
        query: Termo ou pergunta jurídica para buscar no banco vetorial (ex: 'limite de responsabilidade cap', 'SLA mínimo').
        category: Categoria opcional ('LGPD', 'SLA', 'PENALIDADES', 'RESPONSABILIDADE', 'FORO', 'FINANCEIRO' ou 'ALL').

    Returns:
        Dicionário contendo os chunks mais similares com fonte, número da página e score de similaridade.
    """
    results = GLOBAL_VECTOR_ENGINE.search_knowledge_base(query=query, category=category, top_k=4)
    return {
        "query": query,
        "category_filter": category,
        "total_retrieved": len(results),
        "retrieved_chunks": results
    }


def search_contract_pages(query: str) -> Dict[str, Any]:
    """Localiza no banco vetorial de qual página e cláusula do contrato saiu determinada informação.

    Args:
        query: Assunto ou cláusula buscada no contrato (ex: 'multa rescisória 50%', 'foro Delaware', 'valor anual').

    Returns:
        Trechos do contrato com o número exato da página (`page_number`) e identificação da cláusula (`section_id`).
    """
    results = GLOBAL_VECTOR_ENGINE.search_contract_pages(query=query, top_k=3)
    return {
        "query": query,
        "matches": results
    }


def search_historical_benchmarks(contract_topic: str) -> Dict[str, Any]:
    """Consulta precedentes históricos de negociação e benchmarks de preços no Banco Vetorial.

    Args:
        contract_topic: Tópico para comparar com a base histórica (ex: 'preço anual SaaS logístico', 'negociação SLA e foro').
    """
    results = GLOBAL_VECTOR_ENGINE.search_knowledge_base(query=contract_topic, category="FINANCEIRO", top_k=3)
    if not results:
        results = GLOBAL_VECTOR_ENGINE.search_knowledge_base(query=contract_topic, category="ALL", top_k=3)
    return {
        "topic": contract_topic,
        "historical_precedents": results
    }


def get_corporate_compliance_guidelines(category: str = "ALL") -> Dict[str, Any]:
    """Retorna as diretrizes de conformidade e limites de tolerância da empresa (combinado com RAG).

    Args:
        category: Categoria a consultar ('LGPD', 'SLA', 'PENALIDADES', 'RESPONSABILIDADE', 'RESCISAO' ou 'ALL').
    """
    guidelines = {
        "LGPD": {
            "regra": "Cláusula obrigatória de DPA (Data Protection Agreement).",
            "fonte_rag": "politicas_compliance_2026.md • Página 1 • Seção [POL-LGPD-01]",
            "requisitos": [
                "Notificação de incidentes de segurança em até 48 horas (ideal 24h).",
                "Compromisso de expurgo/devolução de dados ao término da relação.",
                "Vedação de transferência internacional de dados sem garantias contratuais adequadas e DPA."
            ],
            "tolerancia": "Tolerância ZERO para ausência de responsabilidade sobre vazamento."
        },
        "SLA": {
            "regra": "Disponibilidade mínima exigida para sistemas SaaS/Cloud.",
            "fonte_rag": "politicas_compliance_2026.md • Página 1 • Seção [POL-SLA-02]",
            "requisitos": [
                "Uptime mínimo de 99.5% ao mês.",
                "Créditos de serviço (Service Credits) progressivos em caso de indisponibilidade.",
                "Direito de rescisão sem multa se o SLA for descumprido reiteradamente."
            ],
            "tolerancia": "SLA inferior a 99.0% ou sem créditos é reprovado."
        },
        "PENALIDADES": {
            "regra": "Teto para multas contratuais e mora.",
            "fonte_rag": "politicas_compliance_2026.md • Página 2 • Seção [POL-FIN-03]",
            "requisitos": [
                "Multa moratória limitada a no máximo 2% por atraso de faturas.",
                "Multa rescisória limitada a no máximo 10% do valor remanescente do contrato.",
                "Reciprocidade estrita de penalidades entre contratante e contratada."
            ],
            "tolerancia": "Multas unilaterais ou superiores a 20% são expressamente vedadas."
        },
        "RESPONSABILIDADE": {
            "regra": "Limitação de responsabilidade patrimonial (Liability Cap).",
            "fonte_rag": "politicas_compliance_2026.md • Página 2 • Seção [POL-JUR-04]",
            "requisitos": [
                "Cap geral de responsabilidade limitado a 12 meses do valor pago pelo contrato.",
                "Exclusão expressa de lucros cessantes e danos indiretos.",
                "Vedação terminante de cláusulas de indenização ilimitada irrestrita."
            ],
            "tolerancia": "Cláusulas sem teto de responsabilidade acionam escalonamento obrigatório para o modelo 3.1 Pro."
        },
        "RESCISAO": {
            "regra": "Prazos para aviso prévio e rescisão imotivada.",
            "fonte_rag": "politicas_compliance_2026.md • Página 2 • Seção [POL-FIN-03]",
            "requisitos": [
                "Aviso prévio para denúncia imotivada de no mínimo 30 e no máximo 60 dias.",
                "Direito de transição assistida dos serviços por no mínimo 30 dias.",
                "Rescisão imediata por justo motivo em caso de falência ou quebra reiterada de SLA."
            ],
            "tolerancia": "Vedada cláusula de fidelidade de 36 meses com renovação tácita sem janela de cancelamento."
        }
    }

    category_upper = category.upper()
    if category_upper in guidelines:
        return {category_upper: guidelines[category_upper]}
    return guidelines


def calculate_contract_risk_index(
    has_unlimited_liability: bool,
    sla_below_standard: bool,
    lgpd_non_compliant: bool,
    penalty_exceeds_cap: bool,
    unilateral_termination_clause: bool = False
) -> Dict[str, Any]:
    """Calcula matematicamente o índice de risco do contrato e avalia o gatilho para o 3.1 Pro."""
    score = 0
    factors = []

    if has_unlimited_liability:
        score += 45
        factors.append("CRÍTICO: Cláusula de responsabilidade/indenização ilimitada (+45 pts)")

    if lgpd_non_compliant:
        score += 25
        factors.append("ALTO: Inadequação com LGPD ou transferência de dados insegura (+25 pts)")

    if sla_below_standard:
        score += 15
        factors.append("MÉDIO: SLA inferior ao padrão operacional corporativo (+15 pts)")

    if penalty_exceeds_cap:
        score += 10
        factors.append("MÉDIO: Penalidades ou multas desproporcionais (+10 pts)")

    if unilateral_termination_clause:
        score += 10
        factors.append("MÉDIO: Desequilíbrio em cláusulas de rescisão (+10 pts)")

    score = min(score, 100)

    if score >= 70:
        level = "CRÍTICO"
        action = "REJEIÇÃO OU RENEGOCIAÇÃO MANDATÓRIA"
    elif score >= 40:
        level = "ALTO"
        action = "NECESSITA REDLINES JURÍDICAS OBRIGATÓRIAS"
    elif score >= 20:
        level = "MODERADO"
        action = "APROVAÇÃO CONDICIONADA A AJUSTES OPERACIONAIS"
    else:
        level = "BAIXO"
        action = "APROVAÇÃO RECOMENDADA"

    requires_pro = bool(has_unlimited_liability or lgpd_non_compliant or score >= 25)

    return {
        "risk_score": score,
        "risk_level": level,
        "requires_3_1_pro_escalation": requires_pro,
        "recommended_action": action,
        "triggering_factors": factors
    }


def calculate_finops_metrics(
    total_input_tokens: int,
    total_output_tokens: int,
    ratio_fast: float = 0.55,
    ratio_standard: float = 0.30,
    ratio_reasoning: float = 0.15
) -> Dict[str, Any]:
    """Calcula a economia financeira obtida pelo roteamento dinâmico (Flash -> 3.1 Pro)."""
    cost_per_m_in_lite = 0.075
    cost_per_m_out_lite = 0.30

    cost_per_m_in_flash = 0.15
    cost_per_m_out_flash = 0.60

    cost_per_m_in_pro = 1.25
    cost_per_m_out_pro = 5.00

    # Abordagem Ingênua (100% no 3.1 Pro)
    all_pro_in_cost = (total_input_tokens / 1_000_000) * cost_per_m_in_pro
    all_pro_out_cost = (total_output_tokens / 1_000_000) * cost_per_m_out_pro
    total_cost_all_pro = all_pro_in_cost + all_pro_out_cost

    # Custo Roteado (Flash + Escalonamento Seletivo 3.1 Pro)
    in_tokens_lite = total_input_tokens * ratio_fast
    out_tokens_lite = total_output_tokens * ratio_fast
    cost_lite = (in_tokens_lite / 1_000_000) * cost_per_m_in_lite + (out_tokens_lite / 1_000_000) * cost_per_m_out_lite

    in_tokens_flash = total_input_tokens * ratio_standard
    out_tokens_flash = total_output_tokens * ratio_standard
    cost_flash = (in_tokens_flash / 1_000_000) * cost_per_m_in_flash + (out_tokens_flash / 1_000_000) * cost_per_m_out_flash

    in_tokens_pro = total_input_tokens * ratio_reasoning
    out_tokens_pro = total_output_tokens * ratio_reasoning
    cost_pro = (in_tokens_pro / 1_000_000) * cost_per_m_in_pro + (out_tokens_pro / 1_000_000) * cost_per_m_out_pro

    total_cost_routed = cost_lite + cost_flash + cost_pro

    savings_usd = max(0.0, total_cost_all_pro - total_cost_routed)
    savings_pct = (savings_usd / total_cost_all_pro * 100) if total_cost_all_pro > 0 else 0.0

    return {
        "total_tokens": total_input_tokens + total_output_tokens,
        "cost_naive_all_pro_usd": round(total_cost_all_pro, 6),
        "cost_routed_adk_usd": round(total_cost_routed, 6),
        "savings_usd": round(savings_usd, 6),
        "savings_percentage": round(savings_pct, 2),
        "tier_distribution": {
            "tier1_flash_share": f"{int(ratio_fast*100)}%",
            "tier2_rag_flash_share": f"{int(ratio_standard*100)}%",
            "tier3_3_1_pro_share": f"{int(ratio_reasoning*100)}%"
        }
    }
