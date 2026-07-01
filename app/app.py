"""Ponto de entrada do Reflex.

É aqui que o app nasce (rx.App) e que as URLs viram telas (add_page).
O Reflex procura este arquivo por causa do app_name="app" no rxconfig.py.

on_load=AuthState.check_auth: roda ANTES de a página abrir, funcionando como
"porteiro" — quem não está logado é mandado de volta pro /login.
"""

import reflex as rx

from pages.login import login_page
from pages.trocar_senha import trocar_senha_page
from pages.dashboard import dashboard_page
from pages.cadastros import cadastros_page
from pages.usuarios import usuarios_page
from pages.ordens import ordens_page
from pages.ordem_form import ordem_form_page
from pages.ordem_detalhe import ordem_detalhe_page
from pages.ordem_print import ordem_print_page
from state.auth_state import AuthState
from state.dominio_state import DominioState
from state.usuario_state import UsuarioState
from state.os_state import OsState
from state.dashboard_state import DashboardState

app = rx.App(
    theme=rx.theme(
        appearance="inherit",
        accent_color="gray",
        font_family="Inter",
    ),
    stylesheets=["/print.css"],  # regras de @media print (esconder botões etc.)
)

# Página pública: a tela de login responde tanto em "/" quanto em "/login".
app.add_page(login_page, route="/", title="Login — Patrimônio")
app.add_page(login_page, route="/login", title="Login — Patrimônio")

# Troca de senha (1º acesso / reset): exige login, mas não força a troca (evita laço).
app.add_page(
    trocar_senha_page,
    route="/trocar-senha",
    title="Trocar senha — Patrimônio",
    on_load=AuthState.exigir_login,
)

# Página protegida: o porteiro (check_auth) exige login antes de abrir.
app.add_page(
    dashboard_page,
    route="/dashboard",
    title="Dashboard — Patrimônio",
    on_load=[AuthState.check_auth, DashboardState.carregar],
)

# Página de cadastros: só admin entra (check_admin) e carrega a 1ª aba ao abrir.
app.add_page(
    cadastros_page,
    route="/cadastros",
    title="Cadastros — Patrimônio",
    on_load=[AuthState.check_admin, DominioState.carregar],
)

# Gestão de usuários: só admin.
app.add_page(
    usuarios_page,
    route="/usuarios",
    title="Usuários — Patrimônio",
    on_load=[AuthState.check_admin, UsuarioState.carregar],
)

# Ordens de Serviço: lista e formulário de criação (qualquer usuário logado).
app.add_page(
    ordens_page,
    route="/ordens",
    title="Ordens de Serviço — Patrimônio",
    on_load=[AuthState.check_operacional, OsState.preparar_lista],
)
app.add_page(
    ordem_form_page,
    route="/ordens/nova",
    title="Nova O.S. — Patrimônio",
    on_load=[AuthState.check_operacional, OsState.carregar_opcoes],
)
# Detalhe: rota DINÂMICA — [os_id] é um curinga que vira parâmetro lido no state.
app.add_page(
    ordem_detalhe_page,
    route="/ordens/[os_id]",
    title="Detalhe da O.S. — Patrimônio",
    on_load=[AuthState.check_operacional, OsState.carregar_detalhe],
)
# Impressão: documento limpo, sem sidebar/topbar.
app.add_page(
    ordem_print_page,
    route="/ordens/[os_id]/imprimir",
    title="Imprimir O.S. — Patrimônio",
    on_load=[AuthState.check_operacional, OsState.carregar_detalhe],
)
