"""Busca nas páginas do contrato. Este arquivo vem pronto: leia para entender, mas não precisa mudar.

1. Indexação: o contrato é cortado em trechos (um por cláusula), e cada trecho guarda a sua página.
2. Busca: cada trecho ganha uma nota pelas palavras da consulta que ele contém; os melhores voltam.

Esta é a versão mais simples possível de RAG (Retrieval-Augmented Generation). No AuditOps de
produção, a nota vem de embeddings (vetores de significado) guardados no AlloyDB com pgvector, e
assim "cancelar o contrato" encontra a cláusula de "rescisão" mesmo sem palavras em comum.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

CONTRATO = Path(__file__).resolve().parents[2] / "contrato_technova.md"

PALAVRAS_VAZIAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas", "um",
    "uma", "para", "por", "com", "que", "qual", "quais", "se", "ao", "aos", "ou", "este", "esta",
    "deste", "desta", "contrato", "clausula", "como", "sobre", "ha", "tem", "pode", "podem", "ser",
}


@dataclass
class Trecho:
    pagina: int
    texto: str


def _normalizar(texto: str) -> list[str]:
    """Minúsculas, sem acento, só palavras com conteúdo."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return [p for p in re.findall(r"[a-z0-9]+", sem_acento) if p not in PALAVRAS_VAZIAS and len(p) > 1]


def dividir_em_trechos(texto: str) -> list[Trecho]:
    """Corta o contrato nos marcadores de página e, dentro de cada página, nas cláusulas (###)."""
    trechos = []
    for numero, conteudo in re.findall(r"--- \[Página (\d+)\] ---\n(.*?)(?=--- \[Página|\Z)", texto, re.S):
        for parte in re.split(r"\n(?=### )", conteudo):
            if parte.strip():
                trechos.append(Trecho(pagina=int(numero), texto=parte.strip()))
    return trechos


TRECHOS = dividir_em_trechos(CONTRATO.read_text(encoding="utf-8"))


def buscar(consulta: str, quantidade: int = 3) -> list[Trecho]:
    """Devolve os trechos com mais palavras em comum com a consulta (só os que têm alguma)."""
    termos = set(_normalizar(consulta))
    notas = [(len(termos & set(_normalizar(t.texto))), t) for t in TRECHOS]
    melhores = sorted((n for n in notas if n[0] > 0), key=lambda n: n[0], reverse=True)
    return [trecho for _, trecho in melhores[:quantidade]]
