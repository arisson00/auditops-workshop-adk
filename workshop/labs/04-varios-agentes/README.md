# Lab 04: uma equipe de agentes

**Tempo:** 15 minutos

**Ao final você terá** uma equipe de quatro agentes que audita o contrato da TechNova como um time de verdade: um extrai as cláusulas, dois especialistas analisam ao mesmo tempo (compliance e risco jurídico) e um quarto escreve o parecer para a diretoria.

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
                        ┌─► compliance ─┐
  contrato ─► extrator ─┤               ├─► parecer ─► diretoria
                        └─► risco ──────┘
            {extracao}     {compliance}      {parecer}
                           {risco}
```

## Passo 1: entrar na pasta e configurar o projeto

```bash
cd labs/04-varios-agentes/starter
cat > auditoria/.env <<EOF
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
GOOGLE_CLOUD_LOCATION=global
EOF
```

Abra `auditoria/agent.py`. Os quatro agentes já estão escritos. Leia as instruções de cada um: repare que o `compliance` e o `risco` leem `{extracao}`, a resposta do extrator. As [políticas de compliance](politicas_compliance.md) da empresa entram nas instruções do `compliance`.

O que falta é **ligar** os agentes.

## Passo 2: completar a equipe

1. **TODO 1:** dê `output_key="compliance"` ao agente `compliance` e `output_key="risco"` ao agente `risco`. Sem isso, as respostas deles não ficam no estado e o parecer não tem o que ler.
2. **TODO 2:** monte a análise em paralelo:
   ```python
   analise = ParallelAgent(name="analise_paralela", sub_agents=[compliance, risco])
   ```
3. **TODO 3:** nas instruções do `parecer`, troque as duas linhas de TODO por `{compliance}` e `{risco}`.
4. **TODO 4:** monte a equipe completa, na ordem:
   ```python
   root_agent = SequentialAgent(name="auditoria", sub_agents=[extrator, analise, parecer])
   ```

## Passo 3: verificar

```bash
python ../verificar.py
```

O script manda o contrato à equipe e mostra **quando cada agente terminou**:

```
Linha do tempo (segundos desde o início):
    8.0s  extrator terminou
   18.8s  compliance terminou
   21.4s  risco terminou
   29.5s  parecer terminou
```

Repare que `compliance` e `risco` terminam quase juntos: os dois começaram ao mesmo tempo, logo depois do extrator. Em sequência, a auditoria levaria uns 10 segundos a mais.

No fim aparece o parecer, por exemplo:

```
**Recomendação:** NÃO ASSINAR SEM AJUSTES, pois o contrato impõe responsabilidade financeira
ilimitada à Contratante, elege arbitragem onerosa no exterior e viola a LGPD...

**O que negociar:**
1. Limitação de responsabilidade e exclusão de danos indiretos (Página 5): ...
```

Os tempos e o texto mudam a cada execução.

## Passo 4: ver no navegador

```bash
adk web --port 8080
```

Abra pela **Visualização da Web** (porta 8080), escolha **auditoria** e cole o conteúdo de `contrato_technova.md`. As respostas aparecem uma por agente, e cada evento mostra qual agente o produziu. No estado da sessão aparecem as quatro chaves: `extracao`, `compliance`, `risco` e `parecer`.

## Experimente (se sobrar tempo)

- Adicione um quinto especialista, `financeiro`, que avalia valor, reajuste e multa, com `output_key="financeiro"`. Coloque-o no `ParallelAgent` e acrescente `{financeiro}` nas instruções do parecer. O tempo total quase não muda. Por quê?
- Troque o `ParallelAgent` por um `SequentialAgent` e compare a linha do tempo.
- Mude uma política no `politicas_compliance.md` (por exemplo, aceite multa de até 50%) e rode de novo. O parecer muda?

## Como isso funciona no AuditOps de verdade

O AuditOps tem a mesma ideia: extrator, compliance e risco jurídico, com as análises independentes rodando ao mesmo tempo. A diferença é que, em produção, cada etapa tem tempo-limite e uma nova tentativa se falhar, e as políticas vêm da busca no AlloyDB (Lab 03), não de um arquivo inteiro nas instruções. No próximo lab entra a outra diferença: nem todos os agentes usam o mesmo modelo.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `✗ TODO ... pendente` | A mensagem diz qual TODO e o que falta. |
| `KeyError: 'Context variable not found: compliance'` | O parecer tentou ler `{compliance}`, mas ninguém gravou essa chave. Confira o TODO 1. |
| `o estado da sessão ficou sem: ...` | Algum `output_key` está com outro nome. |
| O `adk web` dá erro ao abrir o app **auditoria** | O `root_agent` ainda é `None`. Faça o TODO 4. |
| Erros de `404`, `403` ou `429` | Veja a tabela do Lab 01. O `429` é mais comum aqui, porque são 4 chamadas por auditoria: espere 1 minuto. |
| Ainda não funciona | A resposta está em `../solucao/auditoria/`. |

## Próximo lab

Todos os agentes desta equipe usam o Gemini Flash. No **Lab 05**, o parecer passa a usar o **Gemini Pro**, mais caro e mais cuidadoso, mas só quando a análise encontra risco. Contrato limpo fica no Flash. É assim que o AuditOps controla o custo.
