"""Tela de login — a única página pública do sistema.

É um rx.form de verdade, com campos nomeados e atributos autocomplete. Isso é o que faz
o NAVEGADOR reconhecer a tela como login e oferecer salvar/preencher as credenciais.
No envio, on_submit=AuthState.login recebe {"username": ..., "password": ...}.
"""

import reflex as rx

from state.auth_state import AuthState


def _campo(label: str, **input_props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(width="100%", size="3", **input_props),
        spacing="1",
        align="start",
        width="100%",
    )


def login_page() -> rx.Component:
    return rx.center(
        rx.card(
            rx.form.root(
                rx.vstack(
                    rx.center(
                        rx.image(src="/brasao_ceara.svg", width="72px", height="auto"),
                        width="100%",
                    ),
                    rx.vstack(
                        rx.heading("Seção de Patrimônio", size="6"),
                        rx.text(
                            "Ordens de Serviço — TJCE",
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        spacing="1",
                        align="center",
                        width="100%",
                    ),
                    rx.divider(),
                    # name= entra no form_data; auto_complete= é a dica pro navegador.
                    _campo(
                        "Usuário",
                        name="username",
                        placeholder="seu login (CPF)",
                        custom_attrs={"autoComplete": "username"},
                    ),
                    _campo(
                        "Senha",
                        name="password",
                        type="password",
                        placeholder="sua senha",
                        custom_attrs={"autoComplete": "current-password"},
                    ),
                    rx.cond(
                        AuthState.error_message != "",
                        rx.text(AuthState.error_message, color=rx.color("red", 10), size="2"),
                    ),
                    rx.button(
                        "Entrar",
                        type="submit",
                        loading=AuthState.is_loading,
                        width="100%",
                        size="3",
                    ),
                    spacing="4",
                    width="100%",
                ),
                on_submit=AuthState.login,
                reset_on_submit=False,
                width="100%",
            ),
            width="360px",
            padding="28px",
        ),
        width="100%",
        min_height="100vh",
        background_color=rx.color("gray", 2),
    )
