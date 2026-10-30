"""Lab 02: o formato da resposta do extrator.

O Gemini recebe este schema, inclusive as descrições dos campos, e é obrigado a devolver um JSON
que se encaixa nele. As descrições funcionam como instruções campo a campo.
"""

from typing import Literal  # noqa: F401 - você vai usar no TODO 2

from pydantic import BaseModel, Field


class Clausula(BaseModel):
    titulo: str = Field(description="Nome curto da cláusula, ex.: 'Renovação automática'")
    resumo: str = Field(description="O que a cláusula diz e por que importa, em uma frase")
    # TODO 1: adicione o campo `pagina`, um número inteiro (int), com uma descrição que diga
    #         de onde tirar a página (o marcador --- [Página X] ---)
    # TODO 2: adicione o campo `risco`, que só aceita "alto", "medio" ou "baixo".
    #         Dica: use Literal["alto", "medio", "baixo"] como tipo


class ExtracaoContrato(BaseModel):
    partes: list[str] = Field(description="Nomes da contratante e da contratada")
    objeto: str = Field(description="O que está sendo contratado, em uma frase")
    valor_mensal: str | None = Field(description="Valor mensal com a moeda, ou null se não houver")
    prazo_meses: int | None = Field(description="Vigência em meses, ou null se não houver")
    renovacao_automatica: bool = Field(description="true se o contrato se renova sozinho ao final")
    foro: str | None = Field(description="Cidade/comarca do foro, ou null se não houver")
    clausulas: list[Clausula] = Field(description="Todas as cláusulas que merecem atenção, uma por item")
