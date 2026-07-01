"""Estado da sidebar — controla se ela está expandida ou contraída.

Outro rx.State, separado do AuthState de propósito: cada state cuida de UM assunto.
Misturar "estou logado?" com "a sidebar está aberta?" deixaria tudo confuso.
"""

import reflex as rx


class SidebarState(rx.State):
    collapsed: bool = False  # False = expandida (260px) | True = contraída (44px)

    def toggle(self):
        self.collapsed = not self.collapsed

    @rx.var
    def active_route(self) -> str:
        """A URL atual — usada pra destacar o item de menu da página em que você está."""
        return self.router.page.path
