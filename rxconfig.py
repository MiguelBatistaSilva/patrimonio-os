import os

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

# Endereço (nome de rede ou IP) da máquina que HOSPEDA o app.
# - Em desenvolvimento: deixe APP_HOST ausente/vazio no .env → usa localhost.
# - Em produção (máquina do chefe): defina APP_HOST=NOME-DO-PC no .env.
APP_HOST = os.getenv("APP_HOST", "").strip()

config_kwargs = dict(
    app_name="app",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)

# A "pegadinha da rede": em produção, instruímos o frontend a falar com o backend no
# endereço da máquina-host — não em "localhost" (que, no navegador do colega, seria a
# máquina DELE). Sem isso, os outros PCs carregam a tela mas não conectam.
if APP_HOST:
    config_kwargs["api_url"] = f"http://{APP_HOST}:8000"

config = rx.Config(**config_kwargs)
