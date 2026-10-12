"""Leitura da fila do CATINET (Assyst Net) — sem banco, sem Reflex.

Como funciona: um Edge SEM JANELA (Playwright) abre o CATINET, faz o login com o
usuário/senha e, já autenticado, pede à API interna do próprio site (/assystnet/v2/...)
a fila e os detalhes de cada chamado. A API devolve JSON, então não lemos HTML.

É executado COMO PROCESSO À PARTE pela tela de chamados (veja state/catinet_state.py):

    python -m services.catinet_scraper      (entrada: JSON no stdin; saída: JSON no stdout)

Entrada : {"url": "<link da fila>", "usuario": "...", "senha": "...",
           "conhecidos": ["R2484749", ...]}      <- esses não têm o detalhe rebuscado
Saída   : {"chamados": [ {...}, ... ]}   ou   {"erro": "mensagem"}

A senha vai pelo stdin (não pela linha de comando, onde qualquer um a veria na lista de
processos). Este módulo nunca a grava nem a imprime.
"""

import json
import re
import sys
from datetime import datetime
from urllib.parse import quote

# Campos pedidos à API no detalhe de cada chamado (mesma sintaxe que o próprio site usa).
CAMPOS_DETALHE = (
    "formattedReference,dateLogged,affectedUserName,affectedUserTelephone,"
    "affectedUserTelephoneExtension,itemA[name],category[name],serviceOffering[name],"
    "shortDescription,remarks,richRemarks[content]"
)
# Plano B quando a resposta completa vem cortada: sem richRemarks (que repete as Notas).
CAMPOS_DETALHE_ENXUTO = (
    "formattedReference,dateLogged,affectedUserName,affectedUserTelephone,"
    "affectedUserTelephoneExtension,itemA[name],category[name],shortDescription,remarks"
)
AVISO_SEM_NOTAS = "(As Notas deste chamado não puderam ser lidas. Abra o chamado no CATINET.)"
_FILA = re.compile(r"eventMonitor/(\d+)")


class ErroCatinet(Exception):
    """Falha esperada (link errado, login recusado...). A mensagem vai para o operador."""


class RespostaInvalida(ErroCatinet):
    """A API respondeu 200, mas com um JSON quebrado/cortado."""


def analisar_url(url: str) -> tuple[str, str]:
    """'https://host/assystnet/#eventMonitor/6309' -> ('https://host/assystnet/', '6309')."""
    url = (url or "").strip()
    achou = _FILA.search(url)
    if not url.startswith("http") or "#" not in url or not achou:
        raise ErroCatinet(
            "O link da fila não parece certo. Copie do navegador o endereço da fila "
            "(termina em #eventMonitor/NÚMERO)."
        )
    return url.split("#", 1)[0], achou.group(1)


def _texto(valor) -> str | None:
    if valor is None:
        return None
    valor = str(valor).replace("\r\n", "\n").strip()
    return valor or None


def normalizar_evento(linha: dict, detalhe: dict | None) -> dict:
    """Junta a linha da fila com o detalhe do chamado num dicionário plano.

    `linha`   : um item de `events` da fila (tem departamento, item, categoria...).
    `detalhe` : resposta de /events/{id} (tem as Notas e o telefone); pode faltar.
    O detalhe, quando existe, manda: é mais completo que a linha da fila.
    """
    detalhe = detalhe or {}

    def nome(origem: dict, campo: str) -> str | None:
        return _texto((origem.get(campo) or {}).get("name"))

    notas = detalhe.get("remarks") or (detalhe.get("richRemarks") or {}).get("content")
    telefone = _texto(detalhe.get("affectedUserTelephone"))
    ramal = _texto(detalhe.get("affectedUserTelephoneExtension"))
    if telefone and ramal and ramal != telefone:
        telefone = f"{telefone} / {ramal}"
    elif ramal and not telefone:
        telefone = ramal

    data = detalhe.get("dateLogged") or linha.get("dateLogged")
    return {
        "referencia": _texto(detalhe.get("formattedReference") or linha.get("formattedReference")),
        "evento_id": int(linha.get("id") or detalhe.get("id")),
        "data_registro": _data_local(data),
        "solicitante": _texto(detalhe.get("affectedUserName") or linha.get("affectedUserName")),
        "telefone": telefone,
        "departamento": nome(linha, "department"),
        "item": nome(detalhe, "itemA") or nome(linha, "itemA"),
        "categoria": nome(detalhe, "category") or nome(linha, "category"),
        "descricao": _texto(notas) or _texto(detalhe.get("shortDescription")),
    }


def _data_local(texto: str | None) -> str | None:
    """'2026-10-09T17:03:00.000-03:00' -> '2026-10-09T17:03:00' (hora de Fortaleza, sem fuso)."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto).replace(tzinfo=None).isoformat(timespec="seconds")
    except ValueError:
        return None


# ── Parte que usa o navegador (Playwright) ─────────────────────────────────────────

_JS_PEDIR = """async ({url, headers}) => {
    const r = await fetch(url, {credentials: 'same-origin', headers: headers});
    return {status: r.status, texto: await r.text()};
}"""

# Cabeçalhos que o navegador/rede preenchem sozinhos; copiá-los só atrapalharia.
_CABECALHOS_IGNORADOS = {"cookie", "host", "content-length", "connection", "accept-encoding"}


def _guardar_cabecalhos(page, destino: dict) -> None:
    """Copia os cabeçalhos que o PRÓPRIO site manda nos seus pedidos à API.

    A API recusa (403) pedidos que não pareçam vir da página dela; o site costuma exigir
    cabeçalhos próprios. Em vez de adivinhar quais, observamos o primeiro pedido que a
    página faz à API depois do login e repetimos os mesmos nos nossos.
    """

    def ao_pedir(pedido):
        if destino or "/assystnet/v2/" not in pedido.url or "unauthenticated" in pedido.url:
            return
        destino.update(
            {k: v for k, v in pedido.headers.items() if k.lower() not in _CABECALHOS_IGNORADOS}
        )

    page.on("request", ao_pedir)


def _pedir(page, base: str, caminho: str, cabecalhos: dict):
    """GET na API interna, dentro da página (já logada). Devolve o JSON."""
    resposta = page.evaluate(
        _JS_PEDIR, {"url": base + "v2/" + caminho, "headers": {"Accept": "application/json", **cabecalhos}}
    )
    if resposta["status"] != 200:
        raise ErroCatinet(
            f"O CATINET negou o acesso (HTTP {resposta['status']}) em {caminho.split('?')[0]}. "
            f"Resposta: {(resposta.get('texto') or '(vazia)')[:200]}"
        )
    try:
        return json.loads(resposta["texto"])
    except json.JSONDecodeError:
        # Visto na prática: o servidor devolveu o JSON cortado no meio.
        raise RespostaInvalida(
            f"O CATINET devolveu uma resposta incompleta em {caminho.split('?')[0]}."
        ) from None


def _login(page, base: str, usuario: str, senha: str) -> None:
    page.goto(base)
    campo_usuario = page.locator("input[name=j_username]")
    try:
        campo_usuario.wait_for(state="visible", timeout=20000)
    except Exception:
        # Sem formulário de login: o perfil já tinha sessão (uso de teste) ou o site mudou.
        return
    # Digita tecla a tecla (e não .fill): o formulário é feito com widgets Dojo, que só
    # percebem o valor quando recebem os eventos de teclado de verdade.
    campo_usuario.click()
    campo_usuario.press_sequentially(usuario)
    campo_senha = page.locator("input[name=j_password]")
    campo_senha.click()
    campo_senha.press_sequentially(senha)

    status_login = None
    try:
        with page.expect_response(lambda r: "j_security_check" in r.url, timeout=20000) as info:
            page.locator("[data-component-tag=login]").click()
        status_login = info.value.status
    except Exception:
        pass
    # O login do CATINET responde 302 tanto quando aceita quanto quando recusa. Quem
    # diferencia é a página: aceito, o formulário some e o sistema carrega; recusado, o
    # formulário continua lá (às vezes com uma mensagem de erro).
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(1500)
    if campo_usuario.count() and campo_usuario.is_visible():
        caixa = page.locator("[data-dojo-attach-point=loginErrorBox]")
        try:
            motivo = caixa.inner_text(timeout=1000).strip() if caixa.is_visible() else ""
        except Exception:
            motivo = ""
        detalhe = f"o site disse: {motivo}" if motivo else f"HTTP do login: {status_login}"
        raise ErroCatinet(f"O CATINET não aceitou o login ({detalhe}). Confira usuário e senha.")


def _detalhe(page, base: str, evento_id, cabecalhos: dict) -> dict | None:
    """Detalhe de um chamado. Resposta cortada: tenta de novo com menos campos; se ainda
    assim não vier, devolve None (quem chama usa só os dados da fila)."""
    for campos in (CAMPOS_DETALHE, CAMPOS_DETALHE_ENXUTO):
        try:
            return _pedir(page, base, f"events/{evento_id}?fields={quote(campos, safe=',')}", cabecalhos)
        except RespostaInvalida:
            continue
    return None


def buscar_fila(
    url: str,
    usuario: str,
    senha: str,
    conhecidos: set[str] | None = None,
    perfil: str | None = None,
) -> list[dict]:
    """Faz login, lê a fila e devolve os chamados (planos, prontos para gravar).

    Só pede o DETALHE dos que ainda não estão em `conhecidos` — a fila inteira vem numa
    chamada só, mas o detalhe é uma chamada por chamado, então poupamos as repetidas.
    `perfil`: pasta de perfil do navegador (só para testes, reaproveita uma sessão aberta).
    """
    from playwright.sync_api import sync_playwright

    base, fila_id = analisar_url(url)
    conhecidos = conhecidos or set()

    with sync_playwright() as p:
        opcoes = {"channel": "msedge", "headless": True}
        if perfil:
            contexto = p.chromium.launch_persistent_context(perfil, **opcoes)
            navegador = None
        else:
            navegador = p.chromium.launch(**opcoes)
            contexto = navegador.new_context()
        try:
            page = contexto.pages[0] if contexto.pages else contexto.new_page()
            cabecalhos: dict = {}
            _guardar_cabecalhos(page, cabecalhos)
            _login(page, base, usuario, senha)
            fila = _pedir(
                page,
                base,
                f"eventMonitor/{fila_id}?ignoreTooManyRowsException=true"
                "&fields=queryProfile%5Bname%5D%2CcolumnProfile%5Bentries%5D%2Cevents",
                cabecalhos,
            )
            linhas = fila.get("events") or []
            resultado = []
            for linha in linhas:
                ref = linha.get("formattedReference")
                detalhe = None
                falhou = False
                if ref not in conhecidos:
                    detalhe = _detalhe(page, base, linha["id"], cabecalhos)
                    falhou = detalhe is None
                chamado = normalizar_evento(linha, detalhe)
                if falhou:
                    # Um chamado ruim não pode derrubar a busca inteira.
                    chamado["descricao"] = AVISO_SEM_NOTAS
                resultado.append(chamado)
            return resultado
        finally:
            contexto.close()
            if navegador:
                navegador.close()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        entrada = json.loads(sys.stdin.read())
        chamados = buscar_fila(
            entrada["url"],
            entrada["usuario"],
            entrada["senha"],
            set(entrada.get("conhecidos") or []),
            entrada.get("perfil"),
        )
        print(json.dumps({"chamados": chamados}, ensure_ascii=False))
        return 0
    except ErroCatinet as erro:
        print(json.dumps({"erro": str(erro)}, ensure_ascii=False))
        return 1
    except Exception as erro:  # navegador ausente, rede fora do ar...
        print(json.dumps({"erro": f"{type(erro).__name__}: {erro}"[:400]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
