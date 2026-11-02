"""Lab 02: o formato da resposta do extrator.

O Gemini recebe este schema, inclusive as descrições dos campos, e é obrigado a devolver um JSON
que se encaixa nele. As descrições funcionam como instruções campo a campo.

O schema já está pronto. Para personalizar, acrescente campos seguindo o modelo dos que já existem.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Clausula(BaseModel):
    """Uma cláusula que merece atenção. Cada linha abaixo é um campo do JSON."""

    # nome_do_campo: tipo = Field(description="o que o Gemini deve colocar aqui")
    titulo: str = Field(description="Nome curto da cláusula, ex.: 'Renovação automática'")
    resumo: str = Field(description="O que a cláusula diz e por que importa, em uma frase")
    # int: o Gemini é obrigado a devolver um número, não um texto como "página dois"
    pagina: int = Field(description="Número da página do contrato onde a cláusula está (marcador --- [Página X] ---)")
    # Literal: só estes três valores são aceitos, então dá para filtrar e ordenar sem surpresas
    risco: Literal["alto", "medio", "baixo"] = Field(description="Risco para a CONTRATANTE")
    # PERSONALIZE AQUI: acrescente campos por cláusula, ex.:
    # sugestao_ajuste: str = Field(description="Como renegociar esta cláusula, em uma frase")


class ExtracaoContrato(BaseModel):
    """O JSON completo que o extrator devolve."""

    partes: list[str] = Field(description="Nomes da contratante e da contratada")
    objeto: str = Field(description="O que está sendo contratado, em uma frase")
    # "| None": o campo pode vir vazio (null) quando o contrato não traz a informação
    valor_mensal: str | None = Field(description="Valor mensal com a moeda, ou null se não houver")
    prazo_meses: int | None = Field(description="Vigência em meses, ou null se não houver")
    renovacao_automatica: bool = Field(description="true se o contrato se renova sozinho ao final")
    foro: str | None = Field(description="Cidade/comarca do foro, ou null se não houver")
    # Uma lista de outro schema: cada item segue o formato da classe Clausula acima
    clausulas: list[Clausula] = Field(description="Todas as cláusulas que merecem atenção, uma por item")
    # PERSONALIZE AQUI: acrescente campos do contrato, ex.:
    # multa_rescisao: str | None = Field(description="Multa por rescisão antecipada, ou null se não houver")
