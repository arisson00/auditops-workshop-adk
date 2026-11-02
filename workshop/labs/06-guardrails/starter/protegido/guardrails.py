"""Lab 06: as regras dos guardrails, separadas do agente para serem fáceis de revisar.

São duas proteções que agem antes de qualquer texto chegar ao Gemini:
1. Bloqueio: textos que tentam dar ordens ao agente param aqui, e o Gemini nem é chamado.
2. Mascaramento: dados pessoais são trocados por marcadores, e o Gemini nunca os vê (LGPD).

As regras já estão prontas. Para personalizar, acrescente padrões nas listas abaixo.
"""

import re

# Cada item: (padrão, motivo). O padrão é uma expressão regular (regex):
#   \s+  = um ou mais espaços     .*  = qualquer coisa     (a|b) = "a" ou "b"     [cç] = "c" ou "ç"
# re.IGNORECASE: "IGNORE" e "ignore" são a mesma tentativa
PADROES_INJECAO = [
    (r"ignore\s+(todas\s+)?(as\s+)?(instru[cç][oõ]es|regras)", "tentativa de sobrescrever as instruções"),
    (r"esque[cç]a\s+(tudo|as\s+regras|as\s+instru[cç][oõ]es|seu\s+papel)", "tentativa de apagar o contexto"),
    (r"(revele|mostre|imprima)\s+(o\s+seu\s+|as\s+suas\s+)?(prompt|instru[cç][oõ]es)", "tentativa de extrair as instruções"),
    (r"(recomende|aprove|assine)\s+.*(sem\s+ressalvas|sem\s+an[aá]lise|imediatamente)", "tentativa de forçar a aprovação"),
    # PERSONALIZE AQUI: acrescente padrões, ex. a versão em inglês:
    # (r"(ignore|disregard)\s+(all\s+)?(previous|prior)\s+(instructions|guidance)", "tentativa de sobrescrever as instruções (inglês)"),
]

DADOS_PESSOAIS = [
    (r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[CPF]"),
    (r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b", "[EMAIL]"),
    # PERSONALIZE AQUI: acrescente outros dados, ex. telefone celular:
    # (r"\(?\b\d{2}\)?\s?9\d{4}-?\d{4}\b", "[TELEFONE]"),
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
