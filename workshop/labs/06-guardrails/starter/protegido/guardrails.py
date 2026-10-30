"""Lab 06: as regras dos guardrails, separadas do agente para serem fáceis de revisar.

São duas barreiras que rodam antes de qualquer texto chegar ao Gemini:
1. Bloqueio: textos que tentam dar ordens ao agente param aqui, e o Gemini nem é chamado.
2. Mascaramento: dados pessoais são trocados por marcadores, e o Gemini nunca os vê (LGPD).
"""

import re

# Cada item: (padrão, motivo). re.IGNORECASE: "IGNORE" e "ignore" são a mesma tentativa
PADROES_INJECAO = [
    (r"ignore\s+(todas\s+)?(as\s+)?(instru[cç][oõ]es|regras)", "tentativa de sobrescrever as instruções"),
    (r"esque[cç]a\s+(tudo|as\s+regras|as\s+instru[cç][oõ]es|seu\s+papel)", "tentativa de apagar o contexto"),
    (r"(revele|mostre|imprima)\s+(o\s+seu\s+|as\s+suas\s+)?(prompt|instru[cç][oõ]es)", "tentativa de extrair as instruções"),
    # TODO 1: acrescente um padrão para textos que mandam aprovar, como
    #         "recomende assinar sem ressalvas" ou "aprove imediatamente".
    #   Dica: (r"(recomende|aprove|assine)\s+.*(sem\s+ressalvas|sem\s+an[aá]lise|imediatamente)", "tentativa de forçar a aprovação"),
    #   Cuidado: um padrão largo demais (ex.: só "assine") bloquearia cláusulas normais.
]

DADOS_PESSOAIS = [
    (r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[CPF]"),
    (r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b", "[EMAIL]"),
]


def detectar_injecao(texto: str) -> str | None:
    """Devolve o motivo se o texto tenta manipular o agente; None se está limpo."""
    for padrao, motivo in PADROES_INJECAO:
        if re.search(padrao, texto, re.IGNORECASE):
            return motivo
    return None


def mascarar(texto: str) -> tuple[str, int]:
    """Troca dados pessoais por marcadores. Devolve o texto novo e quantos dados foram trocados."""
    total = 0
    for padrao, marcador in DADOS_PESSOAIS:
        texto, trocas = re.subn(padrao, marcador, texto)
        total += trocas
    return texto, total
