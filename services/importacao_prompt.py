"""Monta o prompt que os operadores colam numa IA de chat (ChatGPT, Gemini, Copilot...).

A IA recebe o texto de um SEI ou chamado e devolve as linhas no formato que o parser
(importacao_texto.py) entende. Ela nunca grava nada: o operador cola o resultado na tela
de importação, confere a pré-visualização e só então grava.

O prompt é gerado COM AS LISTAS ATUAIS do cadastro (modalidades e, opcionalmente,
setores). Assim ele nunca fica desatualizado quando o admin mexe nos cadastros.
Python puro, testável sem banco.
"""

_REGRAS = """\
Você vai me ajudar a transformar pedidos de serviço (processos do SEI ou chamados) em linhas de texto para importar no sistema de Ordens de Serviço da Seção de Patrimônio. Siga EXATAMENTE as regras abaixo.

FORMATO
Uma O.S. por linha, com 5 campos separados por ponto e vírgula (;), nesta ordem:
Chamado;Setor;Modalidade;Descrição;Responsável

- Chamado: o número do processo SEI ou do chamado, exatamente como aparece.
- Setor: a unidade que pediu o serviço.{regra_setor}
- Modalidade: UMA das modalidades da lista abaixo, escrita exatamente igual.
- Descrição: resumo curto, em uma frase, do que deve ser feito.
- Responsável: o nome da pessoa de contato, se houver. Se não houver, deixe vazio.
- Os 5 campos estão SEMPRE presentes. Campo vazio fica só com o ponto e vírgula. Exemplo com Responsável vazio:
  8500123-45.2026.8.06.0000;21° Vara Cível;Reparo;Reparar o notebook;
- Nunca use ponto e vírgula dentro de um campo. Se precisar, troque por vírgula.

BENS (ITENS)
Para cada bem citado no pedido, escreva uma linha logo abaixo da O.S. a que ele pertence:
item;Tombo ou Nº de série;Descrição do bem
Se o bem não tem tombo, deixe o primeiro campo vazio:
item;;Descrição do bem
Se o pedido não cita bens, não escreva nenhuma linha item.

REGRAS GERAIS
- Nunca invente informação. O que não estiver no texto fica vazio.
- Se não conseguir identificar o Setor ou a Modalidade, escreva ??? naquele campo (o sistema vai destacar a linha para eu corrigir).
- Se eu colar vários pedidos, escreva uma O.S. para cada um, cada uma com os seus itens logo abaixo.
- Não inclua CPF, telefone, e-mail nem outros dados pessoais.
- Responda SOMENTE com as linhas, dentro de um único bloco de código, sem títulos, sem numeração, sem explicações e sem linhas em branco. Depois do bloco, se houver algo que você não conseguiu preencher ou ficou em dúvida, diga em poucas linhas.

MODALIDADES VÁLIDAS
{modalidades}
{bloco_setores}
EXEMPLO
Texto do pedido:
Processo 8500123-45.2026.8.06.0000. A 21ª Vara Cível solicita o recolhimento de um notebook, tombo 123456, e de um monitor sem patrimônio, para reparo. Contato: Maria.

Sua resposta:
```
8500123-45.2026.8.06.0000;21° Vara Cível;Recolhimento;Recolher notebook e monitor para reparo;Maria
item;123456;Notebook
item;;Monitor
```

Se entendeu, responda apenas "Pronto" e aguarde: vou colar o texto dos pedidos.
"""

_SETOR_SEM_LISTA = (
    " Escreva o nome completo e oficial, sem abreviar, como aparece no documento"
    " (ex.: 21° Vara Cível; Vara Única da Comarca de Milagres)."
)
_SETOR_COM_LISTA = (
    " Escolha na lista de SETORES VÁLIDOS abaixo, escrito exatamente igual."
)


def montar_prompt(modalidades: list[str], setores: list[str] | None = None) -> str:
    """Prompt completo. Com `setores`, inclui a lista (a IA acerta mais, mas o texto fica
    bem maior); sem ela, a IA escreve o nome por extenso e o sistema sugere correções."""
    if setores:
        regra_setor = _SETOR_COM_LISTA
        bloco_setores = "\nSETORES VÁLIDOS\n" + "\n".join(f"- {s}" for s in setores) + "\n"
    else:
        regra_setor = _SETOR_SEM_LISTA
        bloco_setores = ""

    return _REGRAS.format(
        regra_setor=regra_setor,
        modalidades="\n".join(f"- {m}" for m in modalidades),
        bloco_setores=bloco_setores,
    )
