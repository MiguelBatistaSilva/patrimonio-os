"""O "cérebro" da autenticação.

Um rx.State é POO de verdade: junta DADOS (os atributos) com COMPORTAMENTO (os métodos)
num objeto reativo — mexeu num atributo, a tela que o usa se redesenha sozinha.
"""

import reflex as rx

from crud.user import authenticate_user
from crud import user as crud_user
from services.database import SessionLocal


class AuthState(rx.State):
    # Persistidos no navegador (LocalStorage): sobrevivem ao F5 / fechar a aba.
    # Se 'username' está vazio, ninguém está logado.
    username: str = rx.LocalStorage("")
    nome: str = rx.LocalStorage("")
    role: str = rx.LocalStorage("")  # "admin" | "operador"
    # ATENÇÃO: LocalStorage é sempre TEXTO (str). Guardar int/bool aqui não round-trip
    # (bool virava a string "False", que é sempre truthy). Por isso: id como string e a
    # flag como "1"/"".
    user_id: str = rx.LocalStorage("")  # id do usuário logado (vira operador_id da O.S.)
    senha_provisoria: str = rx.LocalStorage("")  # "1" = senha provisória (força troca)

    # Estado do formulário de login (NÃO persistido).
    error_message: str = ""
    is_loading: bool = False

    # Campos da tela de trocar senha.
    f_nova_senha: str = ""
    f_confirma_senha: str = ""

    # Setters dos campos do formulário. Nesta versão do Reflex eles NÃO são gerados
    # automaticamente, então escrevemos à mão: cada um só guarda o que foi digitado.
    def set_f_nova_senha(self, value: str):
        self.f_nova_senha = value

    def set_f_confirma_senha(self, value: str):
        self.f_confirma_senha = value

    @rx.var
    def is_logged_in(self) -> bool:
        return self.username != ""

    @rx.var
    def is_admin(self) -> bool:
        return self.role == "admin"

    @rx.var
    def is_visualizador(self) -> bool:
        return self.role == "visualizador"

    def login(self, form_data: dict):
        """Handler do formulário de login. Lê usuário/senha do form_data.

        Usar um <form> de verdade (em vez de campos avulsos) é o que faz o NAVEGADOR
        reconhecer a tela como login e oferecer salvar/preencher as credenciais.
        """
        self.error_message = ""
        self.is_loading = True
        yield  # manda o "carregando" pra tela ANTES de ir ao banco (que pode demorar)

        db = SessionLocal()
        try:
            user = authenticate_user(
                db, form_data.get("username", ""), form_data.get("password", "")
            )
            if user:
                # Login OK: guarda os dados e limpa o formulário.
                self.username = user.username
                self.nome = user.nome
                self.role = user.role
                self.user_id = str(user.id)
                self.senha_provisoria = "1" if user.senha_provisoria else ""
                # Senha provisória? Manda trocar antes de entrar no sistema.
                if user.senha_provisoria:
                    yield rx.redirect("/trocar-senha")
                else:
                    yield rx.redirect("/dashboard")
            else:
                self.error_message = "Usuário ou senha inválidos."
        finally:
            db.close()              # sempre fecha a sessão do banco
            self.is_loading = False

    def logout(self):
        # Limpa TUDO (senão o LocalStorage manteria o usuário "logado").
        self.username = ""
        self.nome = ""
        self.role = ""
        self.user_id = ""
        self.senha_provisoria = ""
        return rx.redirect("/login")

    def check_auth(self):
        """Porteiro de rota: sem login vai pro login; com senha provisória vai trocar."""
        if not self.is_logged_in:
            return rx.redirect("/login")
        if self.senha_provisoria == "1":
            return rx.redirect("/trocar-senha")

    def check_admin(self):
        """Porteiro de rota: só admin entra; operador volta pro dashboard."""
        if not self.is_logged_in:
            return rx.redirect("/login")
        if self.senha_provisoria == "1":
            return rx.redirect("/trocar-senha")
        if not self.is_admin:
            return rx.redirect("/dashboard")

    def check_operacional(self):
        """Porteiro das telas de O.S.: admin e operador entram; visualizador não.

        É a TRAVA real (não basta esconder o item do menu): mesmo digitando a URL,
        o visualizador é mandado de volta pro Dashboard.
        """
        if not self.is_logged_in:
            return rx.redirect("/login")
        if self.senha_provisoria == "1":
            return rx.redirect("/trocar-senha")
        if self.is_visualizador:
            return rx.redirect("/dashboard")

    def exigir_login(self):
        """on_load da tela de trocar senha: só exige estar logado.

        NÃO força a troca aqui de propósito — senão a própria página redirecionaria
        para si mesma num laço infinito.
        """
        if not self.is_logged_in:
            return rx.redirect("/login")

    def trocar_senha(self):
        """Usuário define a nova senha; ela deixa de ser provisória e ele entra."""
        self.error_message = ""
        if len(self.f_nova_senha) < 4:
            self.error_message = "A nova senha deve ter pelo menos 4 caracteres."
            return
        if self.f_nova_senha != self.f_confirma_senha:
            self.error_message = "As senhas não conferem."
            return
        db = SessionLocal()
        try:
            crud_user.trocar_senha(db, int(self.user_id), self.f_nova_senha)
        finally:
            db.close()
        self.senha_provisoria = ""
        self.f_nova_senha = ""
        self.f_confirma_senha = ""
        # Flush ANTES de navegar: garante que senha_provisoria=False chegue ao
        # navegador antes do check_auth do /dashboard rodar (senão, laço).
        yield
        yield rx.redirect("/dashboard")
