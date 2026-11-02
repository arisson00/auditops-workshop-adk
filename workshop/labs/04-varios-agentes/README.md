# Lab 04: uma equipe de agentes

**Tempo:** 15 minutos

**Ao final você terá** uma equipe de agentes que audita o contrato da TechNova como um time de verdade: um extrai as cláusulas, os especialistas analisam ao mesmo tempo (compliance, risco jurídico **e um especialista criado por você**) e o último escreve o parecer para a diretoria.

Até aqui, cada lab tinha um agente fazendo tudo. Na prática, um agente com uma tarefa estreita e instruções curtas erra menos do que um agente generalista com instruções enormes. E dá para trocar, testar e melhorar cada especialista separadamente.

## O que você vai aprender

| Conceito | Para que serve |
|---|---|
| `SequentialAgent` | Roda os agentes um depois do outro, na ordem da lista. |
| `ParallelAgent` | Roda os agentes ao mesmo tempo. Use quando um não depende do resultado do outro. |
| `output_key` | Grava a resposta de um agente no estado da sessão (você já viu no Lab 02). |
| `{chave}` nas instruções | O ADK troca `{chave}` pelo valor do estado antes de chamar o Gemini. É assim que um agente lê o trabalho do anterior. |

A equipe fica assim:

```
                        ┌─► compliance ──┐
  contrato ─► extrator ─┼─► risco ───────┼─► parecer ─► diretoria
                        └─► (o seu) ─────┘
            {extracao}     {compliance}       {parecer}
                           {risco}
                           {o_seu}
```

## Passo 1: entrar no lab

```bash
lab 04
```

A equipe já vem pronta em `auditoria/agent.py`.

## Passo 2: conhecer a equipe

```bash
cloudshell edit auditoria/agent.py
```

Leia o arquivo de cima para baixo. São quatro agentes, e cada um faz uma coisa só:

| Agente | O que faz | Grava em | Lê |
|---|---|---|---|
| `extrator` | Lista as cláusulas com a página | `extracao` | o contrato |
| `compliance` | Confere contra as [políticas da empresa](politicas_compliance.md) | `compliance` | `{extracao}` |
| `risco` | Aponta os riscos jurídicos | `risco` | `{extracao}` |
| `parecer` | Escreve a recomendação para a diretoria | `parecer` | a análise de cada especialista |

E duas peças ligam os agentes:

- `ParallelAgent(sub_agents=ESPECIALISTAS)`: os especialistas rodam **ao mesmo tempo**, porque nenhum depende do outro.
- `SequentialAgent(sub_agents=[extrator, analise, parecer])`: a ordem da equipe. Primeiro extrai, depois os especialistas analisam, por fim o parecer.

## Passo 3: testar a equipe

No terminal, ainda na pasta do lab, rode:

```bash
python ../verificar.py
```

> Mudou de pasta ou abriu outro terminal? Rode `lab 04` antes.

O script manda o contrato da TechNova à equipe e mostra **quando cada agente terminou**:

```
Linha do tempo (segundos desde o início):
    8.0s  extrator terminou
   18.8s  compliance terminou
   21.4s  risco terminou
   29.5s  parecer terminou
```

Repare que `compliance` e `risco` terminam quase juntos: os dois começaram ao mesmo tempo, logo depois do extrator. No fim aparece o parecer, por exemplo:

```
**Recomendação:** NÃO ASSINAR SEM AJUSTES, pois o contrato impõe responsabilidade financeira
ilimitada à Contratante, elege arbitragem onerosa no exterior e viola a LGPD...
```

Os tempos e o texto mudam a cada execução.

## Passo 4: monte o seu especialista

Agora é a sua vez: acrescente um quinto agente à equipe e veja o parecer mudar. São dois passos.

**1. Crie o especialista.** No `auditoria/agent.py`, procure o bloco `MONTE O SEU ESPECIALISTA`. Já tem um analista **financeiro** pronto, comentado. Para usá-lo, selecione as linhas do `# financeiro = Agent(` até o `# )` e aperte `Ctrl+/` para tirar os `#`.

**2. Coloque-o na equipe.** Logo abaixo do bloco, acrescente o nome dele na lista:

```python
ESPECIALISTAS = [compliance, risco, financeiro]
```

Salve com `Ctrl+S` e rode `python ../verificar.py`. O que muda:

- a linha do tempo ganha o `financeiro`, terminando junto com os outros especialistas: como eles rodam ao mesmo tempo, um especialista a mais quase não alonga essa fase. Já o parecer fica um pouco mais lento, porque passa a ler mais análises;
- aparece a **análise do seu especialista**, antes do parecer;
- o parecer passa a considerar o ponto de vista financeiro. Você não mexeu nas instruções do parecer: ele lê sozinho a análise de cada especialista da lista.

### Outros especialistas prontos para colar

Cole o bloco logo acima da linha `ESPECIALISTAS = [...]`, sem `#` no começo, e acrescente o nome dele na lista.

**ESG** (sustentabilidade e governança):

```python
esg = Agent(
    name="esg",
    model=MODELO,
    description="Avalia o contrato pelo olhar de sustentabilidade e governança (ESG).",
    instruction="""
Você é o analista de ESG da contratante. Com base nas cláusulas extraídas abaixo, aponte até 3
pontos de atenção ambientais, sociais ou de governança (ex.: uso de dados de pessoas, transparência,
subcontratação), cada um com a página. Se não houver, diga isso.

Cláusulas extraídas do contrato:
{extracao}
""",
    output_key="esg",
)
```

**Segurança da informação:**

```python
seguranca = Agent(
    name="seguranca",
    model=MODELO,
    description="Avalia os riscos de segurança da informação e de TI do contrato.",
    instruction="""
Você é o especialista em segurança da informação da contratante. Com base nas cláusulas extraídas
abaixo, aponte os 3 maiores riscos de TI e segurança (vazamento, disponibilidade, localização dos
dados, resposta a incidentes), cada um com a página e o que exigir do fornecedor.

Cláusulas extraídas do contrato:
{extracao}
""",
    output_key="seguranca",
)
```

**Operações** (o que pode parar o dia a dia):

```python
operacoes = Agent(
    name="operacoes",
    model=MODELO,
    description="Avalia o impacto do contrato no dia a dia da operação.",
    instruction="""
Você é o gerente de operações da contratante. Com base nas cláusulas extraídas abaixo, diga o que
pode parar a operação (indisponibilidade, suporte, prazos de reparo) e como se proteger, em até 3
pontos, cada um com a página.

Cláusulas extraídas do contrato:
{extracao}
""",
    output_key="operacoes",
)
```

**Negociador** (estratégia para a reunião com o fornecedor):

```python
negociador = Agent(
    name="negociador",
    model=MODELO,
    description="Prepara a estratégia de negociação com o fornecedor.",
    instruction="""
Você é o negociador de compras da contratante. Com base nas cláusulas extraídas abaixo, monte a
estratégia para a reunião com o fornecedor: o que pedir primeiro, o que aceitar ceder e qual argumento
usar em cada ponto, citando a página.

Cláusulas extraídas do contrato:
{extracao}
""",
    output_key="negociador",
)
```

Dá para colocar vários de uma vez, ex.: `ESPECIALISTAS = [compliance, risco, financeiro, seguranca, negociador]`.

### Crie o seu do zero

Copie qualquer bloco acima e troque três coisas:

| O que trocar | Regra |
|---|---|
| O nome da variável, o `name` e o `output_key` | Os três iguais, só letras minúsculas e `_`, sem repetir o nome de outro agente. Ex.: `juridico_trabalhista` |
| A `description` | Uma frase sobre o que ele faz |
| O papel nas instruções | Quem ele é e o que deve apontar. Mantenha o `{extracao}` e o pedido de citar a página. |

Ideias: trabalhista, tributário, auditoria interna, sustentabilidade, experiência do cliente, ou um especialista do setor da sua empresa.

## Passo 5: ver no navegador

```bash
lab web
```

Abra o link que o `lab web` mostra, escolha **auditoria** e cole o conteúdo de `contrato_technova.md`. As respostas aparecem uma por agente, inclusive a do seu especialista, e cada evento mostra qual agente o produziu. No estado da sessão aparece uma chave por agente.

## Experimente (se sobrar tempo)

- Troque o `ParallelAgent` por `SequentialAgent` e compare a linha do tempo. Quanto tempo a mais leva?
- Mude uma política no `politicas_compliance.md` (por exemplo, aceite multa de até 50%) e rode de novo. O parecer muda?
- Ponha 5 especialistas na equipe. O parecer fica melhor ou só mais longo?

Quer voltar ao original? Rode `git checkout auditoria/`.

## Como isso funciona no AuditOps de verdade

O AuditOps tem a mesma ideia: extrator, compliance e risco jurídico, com as análises independentes rodando ao mesmo tempo. A diferença é que, em produção, cada etapa tem tempo-limite e uma nova tentativa se falhar, e as políticas vêm da busca no AlloyDB (Lab 03), não de um arquivo inteiro nas instruções. No próximo lab entra a outra diferença: nem todos os agentes usam o mesmo modelo.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `lab: command not found` | Prepare o workshop: veja o [README do workshop](../../README.md#antes-de-começar). |
| `✗ não achei a pasta auditoria/` | Você saiu da pasta do lab. Rode `lab 04`. |
| `NameError: name 'financeiro' is not defined` | O nome está na lista `ESPECIALISTAS`, mas o bloco do agente ainda está comentado (com `#`) ou ficou abaixo da lista. O bloco precisa vir **antes** da linha `ESPECIALISTAS = [...]`. |
| `IndentationError` ou `SyntaxError` | Sobrou ou faltou um `#`, um espaço ou uma `"""` no bloco colado. Confira com os blocos deste README, ou rode `git checkout auditoria/` para voltar ao original. |
| `o output_key ... já é usado por outro agente` | Dois agentes com o mesmo `output_key`. Dê um nome diferente ao seu. |
| `o especialista ... está sem output_key` | Faltou a linha `output_key="..."` no bloco do seu especialista. |
| `KeyError: 'Context variable not found: ...'` | Algum agente lê uma `{chave}` que ninguém gravou. Confira se o `output_key` do especialista é igual ao nome dele. |
| Erros de `404`, `403` ou `429` | Veja a tabela do Lab 01. O `429` é mais comum aqui, porque são 4 ou mais chamadas por auditoria: espere 1 minuto. |

## Próximo lab

Todos os agentes desta equipe usam o Gemini Flash. No **Lab 05**, o parecer passa a usar o **Gemini Pro**, mais caro e mais cuidadoso, mas só quando a análise encontra risco. Contrato limpo fica no Flash. É assim que o AuditOps controla o custo.
