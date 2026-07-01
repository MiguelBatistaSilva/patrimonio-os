"""Tela de troca de senha — aparece quando a senha é provisória (1º acesso ou reset).

É standalone (sem sidebar), como o login: enquanto não trocar, o usuário não usa o
sistema. O porteiro check_auth das outras páginas redireciona pra cá até a troca ser feita.
"""

import reflex as rx

from state.auth_state import AuthState


def _campo(label: str, valor, on_change) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(type="password", value=valor, on_change=on_change, width="100%", size="3"),
        spacing="1",
        align="start",
        width="100%",
    )


def trocar_senha_page() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Trocar senha", size="6"),
                rx.text(
                    "Por segurança, defina uma nova senha para continuar.",
                    size="2",
                    color=rx.color("gray", 10),
                ),
                rx.divider(),
                _campo("Nova senha", AuthState.f_nova_senha, AuthState.set_f_nova_senha),
                _campo(
                    "Confirmar nova senha",
                    AuthState.f_confirma_senha,
                    AuthState.set_f_confirma_senha,
                ),
                rx.cond(
                    AuthState.error_message != "",
                    rx.text(AuthState.error_message, color=rx.color("red", 10), size="2"),
                ),
                rx.button(
                    "Salvar e entrar",
                    on_click=AuthState.trocar_senha,
                    width="100%",
                    size="3",
                ),
                rx.button(
                    "Sair",
                    on_click=AuthState.logout,
                    variant="ghost",
                    color_scheme="gray",
                    size="1",
                ),
                spacing="4",
                width="100%",
            ),
            width="380px",
            padding="28px",
        ),
        width="100%",
        min_height="100vh",
        background_color=rx.color("gray", 2),
    )
