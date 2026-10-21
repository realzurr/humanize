"""Testes de paginação (margens parametrizadas, não hard-coded)."""

from __future__ import annotations

from app.services.academic.pagination import PageSide, page_number_position, resolve_margins
from app.services.academic.template_model import Margens, Pagina, Paginacao


def _pagina(mirror: bool = True) -> Pagina:
    return Pagina(
        size="A4",
        mirror=mirror,
        margins_cm=Margens(top_cm=3, bottom_cm=2, left_cm=3, right_cm=2),
        margins_verso_cm=Margens(top_cm=3, bottom_cm=2, left_cm=2, right_cm=3),
    )


def test_anverso_devolve_margens_declaradas() -> None:
    margens = resolve_margins(_pagina(), PageSide.ANVERSO)
    assert (margens.left_cm, margens.right_cm) == (3, 2)


def test_verso_devolve_margens_declaradas() -> None:
    margens = resolve_margins(_pagina(), PageSide.VERSO)
    assert (margens.left_cm, margens.right_cm) == (2, 3)


def test_verso_sem_margem_declarada_espelha() -> None:
    pagina = Pagina(
        mirror=True,
        margins_cm=Margens(top_cm=3, bottom_cm=2, left_cm=3, right_cm=2),
    )
    margens = resolve_margins(pagina, PageSide.VERSO)
    assert (margens.left_cm, margens.right_cm) == (2, 3)


def test_sem_espelhamento_verso_igual_anverso() -> None:
    pagina = Pagina(
        mirror=False,
        margins_cm=Margens(top_cm=3, bottom_cm=2, left_cm=3, right_cm=2),
    )
    margens = resolve_margins(pagina, PageSide.VERSO)
    assert (margens.left_cm, margens.right_cm) == (3, 2)


def test_posicao_de_numero_anverso_e_verso() -> None:
    pagina = _pagina()
    pagina = pagina.model_copy(update={"numbering": Paginacao(position="top_outside")})
    assert page_number_position(pagina, PageSide.ANVERSO) == "top_right"
    assert page_number_position(pagina, PageSide.VERSO) == "top_left"
