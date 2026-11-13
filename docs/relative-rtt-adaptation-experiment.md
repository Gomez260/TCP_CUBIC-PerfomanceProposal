# Experimento: adaptação pelo aumento relativo do RTT

Esta branch contém a automação e a documentação da pesquisa CUBIC-RTT. O repositório ns-3 é um submodule independente e permanece fora do escopo de escrita desta branch.

## Limite de alteração

- Branch autorizada para alterações: `experiment/relative-rtt-adaptation`.
- Branch `master` do repositório principal: não alterar.
- Repositório e commit do submodule `ns3/ns-3-dev-git`: não alterar.
- Não executar scripts que escrevam em arquivos dentro de `ns3/ns-3-dev-git`.

**Atenção:** `scripts/cubic/apply_relative_rtt_adaptation.py` escreve diretamente em `tcp-cubic-rtt.cc` e `tcp-cubic-rtt.h` dentro do submodule. Portanto, esse script não deve ser executado neste fluxo de trabalho. A existência do script não concede autorização para modificar o submodule.

## Hipótese experimental documentada anteriormente

A hipótese anterior propunha utilizar o aumento relativo do RTT observado durante a conexão:

```
relativeIncrease = clamp((RTT_sample - RTT_min) / RTT_min, 0, 1)
EWMA_n = 0.9 * EWMA_(n-1) + 0.1 * relativeIncrease_n
```

e aplicar esse sinal ao parâmetro C. Essa é uma hipótese separada e **não deve ser incorporada nem tratada como parte da implementação atual sem decisão explícita**. A fórmula já existente em `TcpCubicRtt` deve ser preservada.

## Situação de validação

Os resultados atuais não são suficientes para afirmar que a adaptação melhora a justiça entre fluxos. Antes de interpretar resultados, a campanha precisa tratar, entre outros pontos:

- heterogeneidade real de RTT entre fluxos;
- repetibilidade estatística das execuções;
- período de aquecimento e janela de medição;
- dimensionamento explícito da fila do gargalo em múltiplos do BDP;
- faixas de banda e RTT que permitam observar o comportamento CUBIC;
- controle CUBIC com parâmetros fixos equivalentes aos calculados pela variante;
- coexistência entre fluxos CUBIC e CUBIC-RTT;
- grade de parâmetros balanceada e definida antes da análise.

A automação do repositório principal só deve passar a utilizar opções que estejam confirmadas no commit do submodule registrado nesta branch. Não assumir que o código de outra branch ou o `master` do repositório ns-3 corresponde ao commit fixado pelo submodule.

Nenhuma melhoria de throughput, atraso ou Jain fairness deve ser alegada antes de executar as campanhas corrigidas e analisar suas repetições.