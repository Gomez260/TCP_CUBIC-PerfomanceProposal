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

## Campanhas adicionais planejadas

### Convivência entre CUBIC e CUBIC-RTT

O script `scripts/run_coexistence_experiments.sh` prepara uma campanha com oito fluxos concorrentes no mesmo gargalo. Cada classe de atraso de acesso possui dois fluxos: um CUBIC e um CUBIC-RTT. A ordem é alternada para reduzir o confundimento entre algoritmo e índice do fluxo:

| Índice | Algoritmo | Atraso de acesso |
|---:|---|---:|
| 0 | CUBIC | 10 ms |
| 1 | CUBIC-RTT | 10 ms |
| 2 | CUBIC | 30 ms |
| 3 | CUBIC-RTT | 30 ms |
| 4 | CUBIC | 60 ms |
| 5 | CUBIC-RTT | 60 ms |
| 6 | CUBIC | 90 ms |
| 7 | CUBIC-RTT | 90 ms |

A campanha usa, por padrão, gargalo de 10 Mbps, atraso de gargalo de 10/50/100 ms, acesso de 1 Gbps, aquecimento de 20 s, janela medida de 300 s, fila de 1 BDP e cinco repetições: 15 simulações. Alpha e Gamma são os valores baseline (0.25 e 0.05), configuráveis por variáveis de ambiente.

**Objetivo:** comparar os dois algoritmos sob condições concorrentes e RTTs heterogêneos. As métricas devem ser examinadas por fluxo e por algoritmo; Jain calculado sobre todos os oito fluxos, sozinho, não responde se um algoritmo prejudica o outro.

### Variação de cenários

O script `scripts/run_scenario_variation.sh` prepara uma campanha de sensibilidade de cenário com CUBIC-RTT:

- Perfis de acesso:
  - `low`: 5, 10, 15 e 20 ms;
  - `heterogeneous`: 10, 30, 60 e 90 ms;
  - `high`: 30, 60, 90 e 120 ms.
- Banda do gargalo: 10, 50 e 100 Mbps.
- Atraso do gargalo: 10, 50 e 100 ms.
- Quatro fluxos, cinco repetições, aquecimento de 20 s, medição de 300 s e fila de 1 BDP.

Total planejado: 3 perfis × 3 bandas × 3 atrasos × 5 repetições = **135 simulações**.

Essa matriz varia uma configuração por vez de forma sistemática, mas não é um fatorial completo de todas as variáveis de rede possíveis. A fila permanece em 1 BDP para manter esse fator controlado nesta campanha. Uma análise posterior poderá incluir uma campanha específica de sensibilidade de fila.

### Controle de parâmetros fixos

A comparação com parâmetros fixos será feita utilizando a campanha de aproximadamente 600 simulações já existente, conforme os dados e scripts efetivamente disponíveis. Não foi criada uma campanha duplicada. Antes da análise, é necessário identificar no conjunto existente quais execuções correspondem ao CUBIC fixo com os mesmos valores de C e Beta efetivamente calculados pelo CUBIC-RTT. Não se deve presumir equivalência apenas porque Alpha e Gamma coincidem: esses são parâmetros de entrada da adaptação, não necessariamente os valores fixos finais de C e Beta.

### Execução

A partir da raiz do repositório principal:

```bash
bash scripts/run_coexistence_experiments.sh
bash scripts/run_scenario_variation.sh
```

Os scripts assumem que o executável `cubic-experiment` já foi compilado no submodule e que essa versão aceita `--flow_algorithms`, `--access_delays`, `--warmup`, `--random_start_max` e `--queue_bdp`. Eles não compilam nem modificam o submodule. Cada execução é armazenada em diretório próprio e pulada quando já existe um FlowMonitor não vazio.

**Validação obrigatória antes da campanha completa:** executar uma repetição de cada script, conferir o log e o FlowMonitor, confirmar que os oito fluxos da campanha de convivência foram atribuídos aos algoritmos esperados e conferir os atrasos/RTTs observados nos traces. O número planejado não significa que os resultados já foram executados ou validados.

### Análise estatística

A consolidação estatística será feita depois da geração dos dados e gráficos, conforme o plano do trabalho. Para a campanha de convivência, comparar CUBIC e CUBIC-RTT dentro de cada classe de RTT, usando as repetições pareadas pelo mesmo número de execução. Para a variação de cenários, comparar o comportamento entre perfis, bandas e atrasos, sem misturar cenários distintos em uma única média.
