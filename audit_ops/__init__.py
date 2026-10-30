"""Exportação do root_agent para compatibilidade direta com Google ADK (`adk web` / `adk run`)."""

from audit_ops.agent import root_agent, AuditOpsOrchestrator

__all__ = ["root_agent", "AuditOpsOrchestrator"]
