"""Sidebar — o menu lateral expansível/contraível.

Navegação ORIENTADA A DADOS: em vez de escrever cada item na mão, descrevemos os
itens numa lista de NavItem e o código gera tudo num loop. Adicionar uma página vira
UMA linha em NAV_ITEMS. (Era classe de @staticmethod; virou funções soltas.)
"""

import reflex as rx
from dataclasses import dataclass

from state.sidebar_state import SidebarState
from state.auth_state import AuthState
from components.user_menu import user_menu
from components.theme import SIDEBAR_EXPANDED, SIDEBAR_COLLAPSED


# ── Navegação (orientada a dados) ───────────────────────────────────────────────

@dataclass
class NavItem:
    icon: str           # nome do ícone (lucide)
    label: str          # texto que aparece
    href: str           # rota de destino
    section: str = "main"
    admin_only: bool = False           # se True, só admin vê o item
    visivel_visualizador: bool = False  # se True, o papel "visualizador" também vê


# Cresce conforme criamos as telas.
NAV_ITEMS: list[NavItem] = [
    NavItem("layout-dashboard", "Dashboard", "/dashboard", section="main", visivel_visualizador=True),
    NavItem("clipboard-list", "Ordens de Serviço", "/ordens", section="main"),
    NavItem("folder-cog", "Cadastros", "/cadastros", section="admin", admin_only=True),
    NavItem("users-round", "Usuários", "/usuarios", section="admin", admin_only=True),
]

# Rótulo de cada seção agrupada (a "main" não recebe cabeçalho).
NAV_SECTIONS: dict[str, str] = {
    "admin": "Administração",
}


# ── Peças internas ──────────────────────────────────────────────────────────────

def _menu_item(item: NavItem) -> rx.Component:
    is_active = SidebarState.active_route == item.href

    link = rx.link(
        rx.hstack(
            rx.icon(item.icon, size=16, color=rx.color("gray", 10), flex_shrink="0"),
            rx.cond(
                ~SidebarState.collapsed,
                rx.text(
                    item.label,
                    size="1",
                    color=rx.color("gray", 10),
                    font_weight=rx.cond(is_active, "600", "400"),
                    white_space="nowrap",
                ),
                rx.fragment(),
            ),
            align="center",
            spacing="2",
            padding="9px 9px",
            border_radius="6px",
            width="100%",
            background_color=rx.cond(is_active, rx.color("gray", 4), "transparent"),
            _hover={"background_color": rx.cond(is_active, rx.color("gray", 4), rx.color("gray", 3))},
        ),
        href=item.href,
        text_decoration="none",
        width="100%",
        display="block",
    )

    # Visibilidade por papel:
    # - item só-admin: some pra quem não é admin;
    # - item operacional (não marcado p/ visualizador): some pro visualizador.
    if item.admin_only:
        return rx.cond(AuthState.is_admin, link, rx.fragment())
    if not item.visivel_visualizador:
        return rx.cond(AuthState.is_visualizador, rx.fragment(), link)
    return link


def _section_header(label: str) -> rx.Component:
    return rx.cond(
        ~SidebarState.collapsed,
        rx.text(
            label,
            size="1",
            color=rx.color("gray", 10),
            font_weight="600",
            letter_spacing="0.06em",
            text_transform="uppercase",
            padding="12px 8px 4px",
        ),
        rx.box(height="8px"),
    )


def _header() -> rx.Component:
    expanded = rx.box(
        rx.hstack(
            rx.text(
                "Seção de Patrimônio",
                size="2",
                font_weight="600",
                color=rx.color("gray", 12),
                white_space="nowrap",
                overflow="hidden",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("panel-left", size=15),
                on_click=SidebarState.toggle,
                variant="ghost",
                color_scheme="gray",
                size="1",
                cursor="pointer",
            ),
            width="100%",
            align="center",
            padding="10px 8px",
            min_height="44px",
        ),
        padding_x="4px",
        width="100%",
    )

    collapsed = rx.box(
        rx.hstack(
            rx.icon("panel-left", size=16, color=rx.color("gray", 10), flex_shrink="0"),
            align="center",
            padding="5px 8px",
            border_radius="6px",
            width="100%",
            _hover={"background_color": rx.color("gray", 3)},
            cursor="pointer",
        ),
        on_click=SidebarState.toggle,
        padding_x="4px",
        width="100%",
        min_height="44px",
        display="flex",
        align_items="center",
    )

    return rx.box(rx.cond(~SidebarState.collapsed, expanded, collapsed))


def _nav() -> rx.Component:
    # Agrupa os itens por seção, preservando a ordem de NAV_ITEMS.
    groups: dict[str, list[NavItem]] = {}
    for item in NAV_ITEMS:
        groups.setdefault(item.section, []).append(item)

    children = []
    for section, items in groups.items():
        if section in NAV_SECTIONS:
            cabecalho = rx.fragment(
                rx.box(rx.divider(), padding_x="4px", width="100%"),
                _section_header(NAV_SECTIONS[section]),
            )
            # Se a seção só tem itens de admin, o cabeçalho também é só pra admin
            # (senão um operador veria o título "Administração" sem nada embaixo).
            if all(i.admin_only for i in items):
                cabecalho = rx.cond(AuthState.is_admin, cabecalho, rx.fragment())
            children.append(cabecalho)
        for item in items:
            children.append(_menu_item(item))

    return rx.vstack(*children, spacing="1", width="100%", padding_x="4px")


# ── API pública ───────────────────────────────────────────────────────────────

def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            _header(),
            _nav(),
            rx.spacer(),
            rx.box(rx.divider(), padding_x="8px", width="100%"),
            user_menu(),
            height="100%",
            width="100%",
            spacing="2",
            align="start",
            padding_top="12px",
        ),
        background_color=rx.color("gray", 2),
        border_right=f"1px solid {rx.color('gray', 6)}",
        height="100vh",
        width=rx.cond(SidebarState.collapsed, SIDEBAR_COLLAPSED, SIDEBAR_EXPANDED),
        min_width=rx.cond(SidebarState.collapsed, SIDEBAR_COLLAPSED, SIDEBAR_EXPANDED),
        transition="width 0.2s ease, min-width 0.2s ease",
        overflow="hidden",
        position="sticky",
        top="0",
        flex_shrink="0",
    )
