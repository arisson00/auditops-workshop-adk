#!/usr/bin/env python3
"""Script de demonstração CLI do AuditOps 2.0 para o Google Bootcamp.

Demonstra:
1. Orquestração Multi-Agente com Google ADK (`root_agent`)
2. Motor de Busca Vetorial (Agentic RAG) com Rastreabilidade de Página (`contract_page` + `rag_policy_source`)
3. Escalonamento por Regra de Negócio:
   - Camada Flash (`gemini-3.8-flash`): Triagem, Indexação por Página e Auditoria Vetorial RAG
   - Camada Pro (`gemini-3.1-pro-preview`): Acionada cirurgicamente quando há risco crítico
4. Agente Assistente de Insights Executivos, Benchmarks e Barganha
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from audit_ops.agent import AuditOpsOrchestrator


def print_banner(orchestrator: AuditOpsOrchestrator):
    banner = f"""
========================================================================================
   🛡️ GOOGLE BOOTCAMP SHOWCASE: AUDITOPS 2.0 (ADK + VECTOR RAG + INSIGHT ASSISTANT)
========================================================================================
  Orquestração: Google ADK (`root_agent`) | Rastreabilidade: Página & Cláusula Exata
  Model Tiering: {orchestrator.model_fast} (Triagem & RAG) ➔ {orchestrator.model_reasoning} (Escalonamento)
========================================================================================
"""
    print(banner)


def run_showcase():
    orchestrator = AuditOpsOrchestrator()
    print_banner(orchestrator)

    sample_path = os.path.join(os.path.dirname(__file__), "samples", "contrato_saas_enterprise.md")
    with open(sample_path, "r", encoding="utf-8") as f:
        contract_content = f.read()

    print(f"[*] Carregando contrato paginado: {os.path.basename(sample_path)}")
    print("[*] Indexando páginas do contrato e base de conhecimento no Banco Vetorial (RAG)...")
    time.sleep(0.3)

    report = orchestrator.execute_audit(
        contract_text=contract_content,
        contract_name="Contrato SaaS Enterprise",
        simulate_if_no_key=True
    )

    print(f"\n[FASE 1] TRIAGEM & MAPEAMENTO DE PÁGINAS ({orchestrator.model_fast})")
    print(f"    Título:      {report.metadata.title}")
    print(f"    Partes:      {' | '.join(report.metadata.parties)}")
    print(f"    Valor:       {report.metadata.contract_value}  [📄 Página {report.metadata.value_page}]")
    print(f"    Foro:        {report.metadata.jurisdiction}  [📄 Página {report.metadata.jurisdiction_page}]")

    print(f"\n[FASE 2] AUDITORIA DE COMPLIANCE NO BANCO VETORIAL RAG ({orchestrator.model_standard})")
    print(f"    Score Geral: {report.compliance.compliance_score}/100 [{report.compliance.overall_status}]")
    print(f"    Escalar para {orchestrator.model_reasoning}? {'SIM (Gatilho de Regra de Negócio Ativado)' if report.compliance.requires_pro_escalation else 'NÃO (Fast-Track)'}")
    for reason in report.compliance.escalation_reasons:
        print(f"      -> {reason}")

    print("\n    Itens Auditados (com Página do Contrato e Fonte no Banco Vetorial):")
    for issue in report.compliance.issues:
        symbol = "[OK]" if issue.status == "CONFORME" else "[!]"
        print(f"    {symbol} {issue.category} [{issue.status}] — 📄 Contrato: {issue.clause_reference}")
        print(f"        Cláusula:  {issue.evaluated_clause}")
        print(f"        Fonte RAG: 📚 {issue.rag_policy_source}")
        print(f"        Ação:      {issue.suggested_action}")

    print(f"\n[FASE 3] REDLINES JURÍDICAS & RACIOCÍNIO PROFUNDO ({orchestrator.model_reasoning})")
    print(f"    Nível de Risco: [{report.legal_review.overall_risk_level}] | Recomendação: [{report.legal_review.recommendation}]")
    for idx, finding in enumerate(report.legal_review.high_risk_findings, 1):
        print(f"\n    [{idx}] {finding.risk_category.upper()} ({finding.severity}) — 📄 Página {finding.contract_page} ({finding.clause_id})")
        print(f"        Trecho Original: {finding.problematic_excerpt}")
        print(f"        Fonte Redline:   📚 {finding.rag_redline_source}")
        print(f"        Redline Pro:     {finding.suggested_redline}")

    print(f"\n[FASE 4] AGENTE ASSISTENTE DE INSIGHTS & NEGOCIAÇÃO ({orchestrator.model_reasoning} + RAG Histórico)")
    print(f"    Status Benchmark Financeiro: [{report.insights.financial_benchmark_status}]")
    print(f"    Economia Anual Potencial:    {report.insights.potential_annual_savings}")
    print(f"    Detalhe: {report.insights.financial_insight_details}")
    print("\n    Alavancas de Barganha (Trade-offs):")
    for lev in report.insights.negotiation_leverages:
        print(f"      • [📄 Página {lev.contract_page}] {lev.topic}: {lev.recommended_tradeoff}")
        print(f"        Precedente RAG: 📚 {lev.historical_benchmark_rag} | Impacto: {lev.estimated_financial_impact}")

    print("\n" + "=" * 88)
    print("                     FINOPS & EFICIÊNCIA DE MODELOS (FLASH 3.8 -> 3.1 PRO)")
    print("=" * 88)
    f_metrics = report.finops
    print(f"  Modelos: {f_metrics.tier1_model} (Triagem/RAG) -> {f_metrics.tier3_model} (Pro Invocado: {f_metrics.pro_was_invoked})")
    print(f"  Custo Abordagem Ingênua (100% 3.1 Pro):   ${f_metrics.estimated_cost_usd_all_pro:.5f} USD")
    print(f"  Custo AuditOps 2.0 (Roteamento ADK):      ${f_metrics.estimated_cost_usd_routed:.5f} USD")
    print(f"  >> ECONOMIA DE CUSTO OBTIDA:              {f_metrics.estimated_cost_savings_pct:.1f}%")
    print("=" * 88)
    print("\n💡 Dica: Para abrir o Frontend Moderno no navegador, execute: python3 app_server.py")


if __name__ == "__main__":
    run_showcase()
