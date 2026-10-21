"""Relatório de normalização.

O relatório é a saída pública do motor: o que mudou, quanto mudou, quais
regras atuaram e **o que foi protegido**. Ele é a base do painel de
estatísticas da interface e do relatório de conformidade das ondas futuras.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ir.protection import ProtectionCatalog
from app.services.normalizer.rules.base import RuleOccurrence

#: Ordem de severidade, da menor para a maior.
_SEVERIDADES: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}


def _maior_severidade(severidades: list[str]) -> str:
    """Devolve a severidade mais alta entre as informadas."""
    if not severidades:
        return "info"
    return max(severidades, key=lambda item: _SEVERIDADES.get(item, 0))


class OcorrenciaRegra(BaseModel):
    """Uma ocorrência detectada por uma regra."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    count: int
    before: str = ""
    after: str = ""
    severity: str = "info"
    positions: tuple[int, ...] = ()


class Transformacao(BaseModel):
    """Resumo por regra: o que a regra fez, no total."""

    model_config = ConfigDict(frozen=True)

    stage: str = "normalize"
    """Etapa do pipeline. Fixo em ``normalize`` nesta onda."""

    rule_id: str
    description: str = ""
    category: str = "geral"
    count: int = 0
    severity: str = "info"
    before: str = ""
    after: str = ""


class EntidadeProtegida(BaseModel):
    """Entidade protegida detectada no texto."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    level: str = "medium"
    fingerprint: str = ""


class NormalizationReport(BaseModel):
    """Relatório completo de uma execução de normalização."""

    model_config = ConfigDict(frozen=True)

    total_caracteres_antes: int = Field(ge=0)
    total_caracteres_depois: int = Field(ge=0)
    transformacoes: tuple[Transformacao, ...] = ()
    """Resumo por regra, na ordem em que as regras atuaram."""

    ocorrencias: tuple[OcorrenciaRegra, ...] = ()
    """Ocorrências detalhadas, por regra."""

    entidades_protegidas: tuple[EntidadeProtegida, ...] = ()
    """Entidades protegidas detectadas no texto final."""

    regras_desativadas: tuple[str, ...] = ()
    """Regras que não foram aplicadas."""

    avisos: tuple[str, ...] = ()
    """Avisos: perda de conteúdo protegido, regra de alto risco desligada."""

    @property
    def houve_perda(self) -> bool:
        """Indica se houve perda ou alteração de conteúdo protegido."""
        return any(aviso.startswith(("perda:", "alteracao:")) for aviso in self.avisos)


def build_transformacoes(
    ocorrencias: list[RuleOccurrence],
    descricoes: dict[str, str],
    categorias: dict[str, str],
) -> tuple[Transformacao, ...]:
    """Agrega as ocorrências por regra, preservando a ordem de aplicação."""
    agregadas: dict[str, Transformacao] = {}
    for ocorrencia in ocorrencias:
        atual = agregadas.get(ocorrencia.rule_id)
        if atual is None:
            agregadas[ocorrencia.rule_id] = Transformacao(
                rule_id=ocorrencia.rule_id,
                description=descricoes.get(ocorrencia.rule_id, ""),
                category=categorias.get(ocorrencia.rule_id, "geral"),
                count=ocorrencia.count,
                severity=ocorrencia.severity,
                before=ocorrencia.before,
                after=ocorrencia.after,
            )
            continue
        agregadas[ocorrencia.rule_id] = Transformacao(
            rule_id=atual.rule_id,
            description=atual.description,
            category=atual.category,
            count=atual.count + ocorrencia.count,
            severity=_maior_severidade([atual.severity, ocorrencia.severity]),
            before=atual.before,
            after=atual.after,
        )
    return tuple(agregadas.values())


def build_entidades(catalog: ProtectionCatalog) -> tuple[EntidadeProtegida, ...]:
    """Converte o catálogo de entidades em itens serializáveis."""
    return tuple(
        EntidadeProtegida(
            id=entidade.id,
            kind=str(entidade.kind),
            text=entidade.text,
            start=entidade.source_range.start,
            end=entidade.source_range.end,
            level=str(entidade.level),
            fingerprint=entidade.fingerprint,
        )
        for entidade in catalog.iter_entities()
    )
