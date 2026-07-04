"""Versão do sistema (fonte da verdade LOCAL).

Este número é comparado com o version.json publicado no GitHub para decidir se há
atualização. Este arquivo VEM no zip de atualização, então ele se atualiza sozinho:
depois de um update bem-sucedido, o número aqui já reflete a versão nova.

Ao publicar uma versão nova, suba este número E o de version.json (os dois iguais).
Formato: MAIOR.MENOR.CORRECAO  (ex.: 1.0.0 -> 1.0.1 numa correção; -> 1.1.0 numa melhoria).
"""

VERSION = "1.1.0"
