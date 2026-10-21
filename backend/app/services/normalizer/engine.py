"""Motor de normalização determinístico.

O motor aplica um conjunto de regras em **ordem fixa**, sem LLM e sem
efeito colateral: a mesma entrada e o mesmo perfil produzem sempre a mesma
saída.

O fluxo é:

1. o texto é segmentado em trechos **protegidos** e **livres**;
2. cada regra é aplicada apenas aos trechos livres que o seu contrato permite
   alterar;
3. as ocorrências de cada regra são acumuladas em um relatório;
4. o catálogo de entidades protegidas é recalculado sobre o texto final e
   comparado com o inicial — qualquer perda ou alteração vira **aviso** no
   relatório.

A proteção é reavaliada após cada regra que altera o texto, porque os
offsets das entidades protegidas mudam a cada transformação.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.ir.protection import ProtectionCatalog
from app.services.normalizer.profile import NormalizationProfile
from app.services.normalizer.protect import (
    ProtectedSpan,
    build_catalog,
    detect_protected_spans,
    free_spans,
)
from app.services.normalizer.rules import build_default_rules
from app.services.normalizer.rules.base import NormalizationRule, RuleOccurrence
from app.services.normalizer.stats import (
    NormalizationReport,
    OcorrenciaRegra,
    build_entidades,
    build_transformacoes,
)


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Resultado de uma execução do motor."""

    text: str
    """Texto normalizado."""

    report: NormalizationReport
    """Relatório com as contagens, as entidades protegidas e os avisos."""

    catalog: ProtectionCatalog
    """Catálogo de entidades protegidas do texto final."""


class NormalizationEngine:
    """Executa o pipeline determinístico de normalização."""

    def __init__(self, rules: Sequence[NormalizationRule] | None = None) -> None:
        self._rules: list[NormalizationRule] = (
            list(rules) if rules is not None else (build_default_rules())
        )
        self._descricoes: dict[str, str] = {
            regra.rule_id: regra.description for regra in self._rules
        }
        self._categorias: dict[str, str] = {regra.rule_id: regra.category for regra in self._rules}

    @property
    def rules(self) -> tuple[NormalizationRule, ...]:
        """Regras do motor, na ordem do pipeline."""
        return tuple(self._rules)

    def run(self, text: str, profile: NormalizationProfile | None = None) -> NormalizationResult:
        """Normaliza o texto conforme o perfil informado."""
        perfil = profile if profile is not None else NormalizationProfile()
        if not text:
            return NormalizationResult(
                text=text,
                report=NormalizationReport(
                    total_caracteres_antes=0,
                    total_caracteres_depois=0,
                ),
                catalog=build_catalog(text),
            )

        catalog_original = build_catalog(text)
        atual = text
        spans: list[ProtectedSpan] = detect_protected_spans(atual)
        ocorrencias: list[RuleOccurrence] = []
        desativadas: list[str] = []

        for regra in self._rules:
            if not perfil.is_enabled(regra.rule_id, default_enabled=regra.enabled_by_default):
                desativadas.append(regra.rule_id)
                continue

            relevantes = [span for span in spans if span.kind in regra.protected_kinds]
            livres = free_spans(atual, relevantes)
            if not livres:
                continue

            novo_texto, ocorrencias_regra = self._aplicar_em_trechos(regra, atual, livres)
            if not ocorrencias_regra:
                continue
            ocorrencias.extend(ocorrencias_regra)
            if novo_texto != atual:
                atual = novo_texto
                spans = detect_protected_spans(atual)

        catalog_final = build_catalog(atual)
        avisos = self._verificar_protegidos(catalog_original, catalog_final)
        avisos.extend(self._avisar_regras_de_risco(perfil, desativadas))

        report = NormalizationReport(
            total_caracteres_antes=len(text),
            total_caracteres_depois=len(atual),
            transformacoes=build_transformacoes(ocorrencias, self._descricoes, self._categorias),
            ocorrencias=tuple(
                OcorrenciaRegra(
                    rule_id=ocorrencia.rule_id,
                    count=ocorrencia.count,
                    before=ocorrencia.before,
                    after=ocorrencia.after,
                    severity=ocorrencia.severity,
                    positions=ocorrencia.positions,
                )
                for ocorrencia in ocorrencias
            ),
            entidades_protegidas=build_entidades(catalog_final),
            regras_desativadas=tuple(desativadas),
            avisos=tuple(avisos),
        )
        return NormalizationResult(text=atual, report=report, catalog=catalog_final)

    def _aplicar_em_trechos(
        self,
        regra: NormalizationRule,
        texto: str,
        livres: list[tuple[int, int]],
    ) -> tuple[str, list[RuleOccurrence]]:
        """Aplica a regra a cada trecho livre e remonta o texto."""
        partes: list[str] = []
        cursor = 0
        ocorrencias: list[RuleOccurrence] = []

        for inicio, fim in livres:
            partes.append(texto[cursor:inicio])
            segmento = texto[inicio:fim]
            resultado = regra.apply(segmento)
            partes.append(resultado.text)
            for ocorrencia in resultado.occurrences:
                ocorrencias.append(_reposicionar(ocorrencia, inicio))
            cursor = fim

        partes.append(texto[cursor:])
        return "".join(partes), ocorrencias

    def _verificar_protegidos(
        self,
        original: ProtectionCatalog,
        final: ProtectionCatalog,
    ) -> list[str]:
        """Compara os catálogos e sinaliza perda ou alteração."""
        avisos: list[str] = []
        for fingerprint in original.missing_fingerprints(final):
            avisos.append(f"perda: entidade protegida {fingerprint} não foi preservada.")
        for entidade, fingerprint in original.changed_fingerprints(final):
            avisos.append(
                f"alteracao: entidade protegida {entidade.id} "
                f"({entidade.kind}) foi alterada ({fingerprint})."
            )
        return avisos

    def _avisar_regras_de_risco(
        self,
        perfil: NormalizationProfile,
        desativadas: list[str],
    ) -> list[str]:
        """Avisa sobre regras de alto risco que ficaram desligadas."""
        avisos: list[str] = []
        for regra in self._rules:
            if regra.rule_id not in desativadas:
                continue
            if regra.touches_protected_content and regra.rule_id not in perfil.enabled_rules:
                avisos.append(
                    f"atencao: a regra {regra.rule_id} foi mantida desligada "
                    "porque pode alterar notação científica."
                )
        return avisos


def _reposicionar(ocorrencia: RuleOccurrence, deslocamento: int) -> RuleOccurrence:
    """Desloca as posições da ocorrência para o texto completo."""
    if deslocamento == 0:
        return ocorrencia
    return RuleOccurrence(
        rule_id=ocorrencia.rule_id,
        count=ocorrencia.count,
        before=ocorrencia.before,
        after=ocorrencia.after,
        severity=ocorrencia.severity,
        positions=tuple(posicao + deslocamento for posicao in ocorrencia.positions),
    )
