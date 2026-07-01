"""Configurações de NEGÓCIO do sistema — botões que o desenvolvedor ajusta.

Não confundir com o rxconfig.py (esse é a configuração do framework Reflex).
Aqui ficam regras do domínio que podem mudar com o cliente, isoladas num lugar só.
"""

# Número da Ordem de Serviço = prefixo + contador com nº fixo de dígitos.
#   OS_PREFIXO="H", OS_DIGITOS=4  ->  H0001, H0002, H0003, ...
# A regra real do prefixo ainda será confirmada com o cliente (na planilha apareceram
# "C0001" na lista e "H0740" ao lado do fórum — "H" pode ser código da unidade).
# Quando soubermos, basta trocar aqui.
OS_PREFIXO = "J"
OS_DIGITOS = 4
