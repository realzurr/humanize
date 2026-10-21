"""Carregamento e resolução de templates acadêmicos.

Implementa a precedência do `ADR-0007`:

    instituição  >  template do tipo de documento  >  norma geral ABNT

* ``extends`` resolve a herança entre templates;
* um perfil institucional sobrescreve **apenas** as regras que declara;
* cada sobreposição gera um :class:`Conflito` registrado, nunca ocultado;
* fontes institucionais que referenciam norma superada são sinalizadas.

Os templates vivem em ``templates/abnt/**`` e ``templates/institutions/**``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.services.academic.template_model import (
    Conflito,
    Fonte,
    Template,
    TemplateResolved,
)

#: Normas com edição vigente (para sinalizar fonte institucional desatualizada).
VIGENTES: dict[str, str] = {
    "ABNT NBR 14724": "2024",
    "ABNT NBR 6023": "2025",
    "ABNT NBR 10520": "2023",
    "ABNT NBR 6022": "2018",
    "ABNT NBR 6024": "2012",
    "ABNT NBR 6027": "2012",
    "ABNT NBR 6028": "2021",
    "ABNT NBR 6029": "2023",
    "ABNT NBR 6034": "2004",
    "ABNT NBR 10719": "2025",
    "ABNT NBR 15287": "2025",
}

#: Chaves de regra que um perfil institucional pode sobrescrever.
_RULE_KEYS = ("page", "typography", "elements", "styles", "sections")


class TemplateNotFoundError(KeyError):
    """Template inexistente no catálogo."""


class TemplateRegistry:
    """Catálogo e resolvedor de templates."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._raw: dict[str, dict[str, Any]] = {}
        self._carregar()

    def _carregar(self) -> None:
        for arquivo in sorted(self._base_dir.rglob("*.yaml")):
            try:
                dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                continue
            if isinstance(dados, dict) and dados.get("id"):
                self._raw[str(dados["id"])] = dados

    def ids(self) -> list[str]:
        """Identificadores de todos os templates carregados."""
        return sorted(self._raw)

    def exists(self, template_id: str) -> bool:
        return template_id in self._raw

    def raw(self, template_id: str) -> dict[str, Any]:
        if template_id not in self._raw:
            raise TemplateNotFoundError(template_id)
        return self._raw[template_id]

    def get(self, template_id: str) -> Template:
        """Devolve o template com a herança (``extends``) já resolvida."""
        return Template.model_validate(self._flatten(template_id))

    def resolve(self, template_id: str, institution_id: str | None = None) -> TemplateResolved:
        """Resolve o template e, opcionalmente, aplica o perfil institucional.

        A aplicação do perfil institucional registra os conflitos entre o
        valor da instituição e o da norma (ou do template), sem nunca ocultar
        a substituição.
        """
        base = self._flatten(template_id)
        conflitos: list[Conflito] = []
        sobrepostas: list[str] = []

        if institution_id:
            institucional = self._flatten(institution_id)
            base, sobrepostas, conflitos = self._aplicar_institucional(base, institucional)

        return TemplateResolved(
            template=Template.model_validate(base),
            conflicts=tuple(conflitos),
            overrides=tuple(sobrepostas),
        )

    def _flatten(self, template_id: str) -> dict[str, Any]:
        """Devolve o dict do template com a cadeia ``extends`` mesclada."""
        cadeia = self._cadeia(template_id)
        resultado: dict[str, Any] = {}
        for item in cadeia:
            resultado = _merge(resultado, item)
        return resultado

    def _cadeia(self, template_id: str) -> list[dict[str, Any]]:
        """Devolve a cadeia de herança, da raiz até o template pedido."""
        if template_id not in self._raw:
            raise TemplateNotFoundError(template_id)
        cadeia: list[dict[str, Any]] = []
        atual = template_id
        visitados: set[str] = set()
        while atual and atual not in visitados:
            visitados.add(atual)
            dados = self._raw[atual]
            cadeia.append(dados)
            atual = dados.get("extends") or ""
        cadeia.reverse()  # raiz primeiro
        return cadeia

    def _aplicar_institucional(
        self,
        base: dict[str, Any],
        institucional: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], list[Conflito]]:
        """Aplica o perfil institucional e registra os conflitos.

        Apenas as chaves de regra (page/typography/elements/styles/sections)
        são sobrescritas; o id, kind e demais metadados do template base são
        preservados.
        """
        regras = {chave: valor for chave, valor in institucional.items() if chave in _RULE_KEYS}
        conflitos: list[Conflito] = []

        fonte_principal = _primeira_fonte(institucional)
        sobrepostas = _scalar_diffs(base, regras)
        for caminho, valor_norma, valor_instituicao in sobrepostas:
            conflitos.append(
                Conflito(
                    rule_id=caminho,
                    norm_value=valor_norma,
                    institution_value=valor_instituicao,
                    institution_source=fonte_principal,
                    severity="warning",
                )
            )

        for fonte_raw in institucional.get("sources", []):
            norm = fonte_raw.get("norm", "")
            vigente = VIGENTES.get(norm)
            if vigente and fonte_raw.get("edition") != vigente:
                conflitos.append(
                    Conflito(
                        rule_id=f"fonte.{norm}",
                        norm_value=f"{norm}:{vigente}",
                        institution_value=f"{norm}:{fonte_raw.get('edition', '')}",
                        institution_source=_fonte_raw(fonte_raw),
                        severity="warning",
                    )
                )

        mesclado = _merge(base, regras)
        return mesclado, [caminho for caminho, _, _ in sobrepostas], conflitos


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Mescla ``override`` sobre ``base`` (dicts recursivamente; listas trocam).

    A lista ``sources`` é a exceção: é concatenada, para que o template filho
    acumule as fontes do pai.
    """
    resultado = dict(base)
    for chave, valor in override.items():
        if chave == "sources" and isinstance(valor, list):
            resultado[chave] = _deduplicar_fontes(resultado.get(chave, []) + valor)
        elif isinstance(valor, dict) and isinstance(resultado.get(chave), dict):
            resultado[chave] = _merge(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado


def _deduplicar_fontes(fontes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vistas: set[tuple[str, str]] = set()
    resultado: list[dict[str, Any]] = []
    for fonte in fontes:
        chave = (str(fonte.get("norm", "")), str(fonte.get("edition", "")))
        if chave in vistas:
            continue
        vistas.add(chave)
        resultado.append(fonte)
    return resultado


def _scalar_diffs(
    base: dict[str, Any], override: dict[str, Any], caminho: str = ""
) -> list[tuple[str, str, str]]:
    """Diferenças de valores escalares entre ``override`` e ``base``."""
    diffs: list[tuple[str, str, str]] = []
    for chave, valor in override.items():
        caminho_atual = f"{caminho}.{chave}" if caminho else chave
        if chave in (
            "sources",
            "id",
            "version",
            "kind",
            "extends",
            "institution",
            "title",
            "description",
        ):
            continue
        if isinstance(valor, dict) and isinstance(base.get(chave), dict):
            diffs.extend(_scalar_diffs(base[chave], valor, caminho_atual))
        elif base.get(chave) != valor:
            diffs.append((caminho_atual, _stringify(base.get(chave)), _stringify(valor)))
    return diffs


def _stringify(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    return str(valor)


def _primeira_fonte(institucional: dict[str, Any]) -> Fonte | None:
    fontes = institucional.get("sources", [])
    return _fonte_raw(fontes[0]) if fontes else None


def _fonte_raw(raw: Any) -> Fonte | None:
    if not isinstance(raw, dict):
        return None
    try:
        return Fonte.model_validate(raw)
    except Exception:
        return None
