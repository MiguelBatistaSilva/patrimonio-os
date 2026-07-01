"""Topbar — a barra fina no topo da área de conteúdo.

Por ora só tem o sino de notificações (decorativo). Cresce depois conforme precisarmos.
"""

import reflex as rx


def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.spacer(),
            rx.icon("bell", size=18, color=rx.color("gray", 10), cursor="pointer"),
            padding="0 24px",
            align="center",
            width="100%",
            height="100%",
        ),
        background_color=rx.color("gray", 1),
        border_bottom=f"1px solid {rx.color('gray', 6)}",
        width="100%",
        height="44px",
        flex_shrink="0",
    )
