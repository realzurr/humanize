"""Configuração de página e paginação.

As margens da NBR 14724:2024 são **parametrizadas** no template
(``templates/**``) e apenas lidas aqui — nunca hard-coded. Este módulo
resolve as margens do anverso e do verso, com espelhamento quando o template
declara impressão anverso/verso.
"""

from __future__ import annotations

from enum import StrEnum

from app.services.academic.template_model import Margens, Pagina


class PageSide(StrEnum):
    """Lado da folha."""

    ANVERSO = "anverso"
    VERSO = "verso"


def resolve_margins(page: Pagina, side: PageSide) -> Margens:
    """Devolve as margens do lado pedido.

    * anverso → ``page.margins_cm``;
    * verso → ``page.margins_verso_cm``, quando declarado; caso contrário,
      as margens do anverso **espelhadas** (troca esquerda/direita) quando a
      impressão é anverso/verso, ou as mesmas do anverso.
    """
    if side is PageSide.ANVERSO:
        return page.margins_cm
    if page.margins_verso_cm is not None:
        return page.margins_verso_cm
    if page.mirror:
        return Margens(
            top_cm=page.margins_cm.top_cm,
            bottom_cm=page.margins_cm.bottom_cm,
            left_cm=page.margins_cm.right_cm,
            right_cm=page.margins_cm.left_cm,
        )
    return page.margins_cm


def page_number_position(page: Pagina, side: PageSide) -> str:
    """Resolve a posição do número de página para o lado dado.

    ``top_outside`` significa canto superior direito no anverso e canto
    superior esquerdo no verso (NBR 14724:2024 §5.4).
    """
    position = page.numbering.position
    if position != "top_outside":
        return position
    return "top_right" if side is PageSide.ANVERSO else "top_left"
