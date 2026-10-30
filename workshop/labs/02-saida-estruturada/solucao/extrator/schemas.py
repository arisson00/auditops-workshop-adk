"""Lab 02 (solução): o formato da resposta do extrator.

O Gemini recebe este schema, inclusive as descrições dos campos, e é obrigado a devolver um JSON
que se encaixa nele. As descrições funcionam como instruções campo a campo.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Clausula(BaseModel):
    titulo: str = Field(description="Nome curto da cláusula, ex.: 'Renovação automática'")
    resumo: str = Field(description="O que a cláusula diz e por que importa, em uma frase")
    pagina: int = Field(description="Número da página do contrato onde a cláusula está (marcador --- [Página X] ---)")
    risco: Literal["alto", "medio", "baixo"] = Field(description="Risco para a CONTRATANTE")


class ExtracaoContrato(BaseModel):
    partes: list[str] = Field(description="Nomes da contratante e da contratada")
    objeto: str = Field(description="O que está sendo contratado, em uma frase")
    valor_mensal: str | None = Field(description="Valor mensal com a moeda, ou null se não houver")
    prazo_meses: int | None = Field(description="Vigência em meses, ou null se não houver")
    renovacao_automatica: bool = Field(description="true se o contrato se renova sozinho ao final")
    foro: str | None = Field(description="Cidade/comarca do foro, ou null se não houver")
    clausulas: list[Clausula] = Field(description="Todas as cláusulas que merecem atenção, uma por item")
