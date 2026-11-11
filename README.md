# TCP CUBIC-RTT — ns-3 Experiment Environment

Repositório de implementação e experimentação de uma variante do TCP CUBIC com adaptação baseada em RTT. Este README documenta **como o código está organizado, como uma simulação é montada, quais dados são gerados e como os scripts processam esses dados**.

O documento descreve o funcionamento do repositório. A fundamentação teórica, a discussão dos resultados e as conclusões da pesquisa pertencem ao texto do TCC, não a esta documentação.

---

## 1. Mapa rápido do projeto

O projeto possui três partes principais:

1. **Simulador (C++ / ns-3):** implementa o algoritmo TCP CUBIC-RTT e executa os cenários de rede.
2. **Automação (Shell):** percorre as combinações de cenários, algoritmos, parâmetros e repetições.
3. **Processamento (Python):** lê os arquivos gerados pelo ns-3, associa métricas aos fluxos TCP e produz CSVs e relatórios de validação.

Fluxo de execução:

```text
run_robustness_experiments.sh
             |
             v
       ns-3 / C++
             |
             +----> FlowMonitor (.flowmonitor)
             |
             +----> TCP traces (.data)
             |
             +----> logs de execução
                         |
                         v
             analyze_robustness_experiments.py
                         |
                         v
                consolidate_results.py
                         |
              +----------+----------+
              |                     |
              v                     v
       resumo_simulacoes.csv  metricas_fluxos.csv
                                    |
                                    v
                         relatorio_validacao.txt
```

## 2. Organização do repositório

```text
TCP_CUBIC-PerfomanceProposal/
|
|-- ns3/
|   \-- ns-3-dev-git/                 # Submodule com o ns-3 modificado
|       |-- src/internet/model/
|       |   |-- tcp-cubic-rtt.cc
|       |   \-- tcp-cubic-rtt.h
|       \-- examples/tcp/
|           \-- cubic-experiment.cc   # Topologia, aplicações e instrumentação
|
|-- scripts/
|   \-- cubic/
|       |-- analyze_results.py
|       |-- consolidate_results.py
|       |-- analyze_parameter_experiments.py
|       |-- analyze_robustness_experiments.py
|       \-- run_scenarios.sh
|
|-- run_parameter_experiments.sh
|-- run_robustness_experiments.sh
|-- robustness_execution.log
|-- results/
|   |-- Cubic/
|   |-- Bbr/
|   |-- CubicRtt/
|   |-- consolidated/
|   |-- parameter_experiments/
|   \-- robustness_experiments/
|       |-- <scenario>/
|       |-- consolidated/
|       \-- ...
|
|-- .gitmodules
\-- README.md
```

O diretório `ns3/ns-3-dev-git` é um **submodule Git**. O repositório principal registra um commit específico do repositório do ns-3; por isso, clonar apenas o repositório principal sem inicializar os submodules não baixa o código do simulador.

Os diretórios de resultados são organizados por campanha. Os arquivos brutos de cada execução ficam separados dos CSVs consolidados.

## 3. Código de simulação

### 3.1 `cubic-experiment.cc`

Arquivo:

`ns3/ns-3-dev-git/examples/tcp/cubic-experiment.cc`

Esse é o programa principal de cada execução. Ele recebe os parâmetros pela linha de comando, constrói a topologia, instala a pilha TCP, cria os fluxos de tráfego e, quando habilitados, registra traces e dados do FlowMonitor.

Entre os parâmetros configuráveis estão:

| Parâmetro | Função |
| --- | --- |
| `transport_prot` | Variante TCP utilizada (`TcpCubic`, `TcpBbr`, `TcpCubicRtt`) |
| `num_flows` | Quantidade de fluxos TCP concorrentes |
| `bandwidth` | Largura de banda do enlace de gargalo |
| `delay` | Atraso do enlace de gargalo |
| `access_bandwidth` | Largura de banda dos enlaces de acesso |
| `access_delay` | Atraso de acesso comum a todos os fluxos |
| `access_delays` | Atrasos individuais de acesso, quando especificados |
| `duration` | Duração da simulação |
| `run` | Índice da repetição, usado para configurar a execução aleatória |
| `tracing` | Habilita os traces TCP |
| `flow_monitor` | Habilita a saída do FlowMonitor |
| `results_dir` | Diretório dos arquivos da execução |
| `queue_disc_type` | Tipo de disciplina de fila |
| `sack` | Habilita ou desabilita SACK |
| `recovery` | Algoritmo de recuperação TCP |

Os valores padrão estão definidos no próprio arquivo C++. Os scripts de campanha passam explicitamente os parâmetros que variam entre as execuções.

### 3.2 Topologia

O experimento constrói uma topologia com dois gateways conectados por um enlace de gargalo. Os nós de origem se conectam ao primeiro gateway por enlaces de acesso; os destinos se conectam ao segundo gateway por seus próprios enlaces de acesso.

Representação lógica:

```text
Origens / clientes                 Destinos / servidores
       |                                     ^
       v                                     |
  Gateway A  ===== enlace de gargalo ===== Gateway B
                 banda e atraso variáveis
```

Cada fluxo possui uma origem e um destino próprios. A quantidade de fluxos é configurada por `num_flows`. Os enlaces de acesso e o enlace de gargalo podem ter parâmetros diferentes.

O FlowMonitor coleta estatísticas dos fluxos IP. Os traces TCP são conectados aos sockets TCP dos nós de origem, permitindo observar o estado de cada conexão transmissora.

### 3.3 Implementação `TcpCubicRtt`

Arquivos:

- `ns3/ns-3-dev-git/src/internet/model/tcp-cubic-rtt.h`
- `ns3/ns-3-dev-git/src/internet/model/tcp-cubic-rtt.cc`

A classe `TcpCubicRtt` é uma implementação independente de `TcpCongestionOps`, registrada no sistema de tipos do ns-3 como `ns3::TcpCubicRtt`.

Além dos mecanismos herdados da implementação CUBIC utilizada como base, a variante possui parâmetros próprios para o ajuste adaptativo:

| Atributo | Papel no código |
| --- | --- |
| `Alpha` | Parâmetro de controle da adaptação |
| `Gamma` | Parâmetro de controle da adaptação |
| `RttReference` | RTT de referência |
| `BetaMin` / `BetaMax` | Limites do parâmetro Beta adaptativo |
| `C` | Fator de escala CUBIC |

As funções `CalculateAdaptiveC()` e `CalculateAdaptiveBeta()` concentram os cálculos dos parâmetros adaptativos. A amostragem e atualização de RTT ocorrem nos métodos de operação do algoritmo, como `PktsAcked()`; a evolução da janela é tratada por `IncreaseWindow()`, e a resposta à indicação de congestionamento envolve `GetSsThresh()`.

Os valores efetivos e as expressões matemáticas devem ser consultados no código-fonte versionado do submodule. Para alterar ou estudar a proposta, o ponto de partida é a classe `TcpCubicRtt`, não o programa de topologia.

Os atributos podem ser passados ao ns-3 pela linha de comando, por exemplo:

```bash
--ns3::TcpCubicRtt::Alpha=0.25
--ns3::TcpCubicRtt::Gamma=0.05
```

## 4. Instrumentação: arquivos produzidos por uma simulação

Quando `--tracing=true`, o experimento registra traces associados a cada fluxo. Os arquivos usam o prefixo `CubicExperiment` e o índice do fluxo.

Exemplos:

```text
CubicExperiment-flow0-cwnd.data
CubicExperiment-flow0-rtt.data
CubicExperiment-flow0-inflight.data
CubicExperiment-flow0-ssth.data
CubicExperiment-flow0-rto.data
CubicExperiment-flow0-next-tx.data
CubicExperiment-flow0-next-rx.data
```

Os arquivos de trace são séries temporais em texto, normalmente com duas colunas:

```text
tempo_em_segundos valor
```

| Trace | Conteúdo | Unidade do valor gravado |
| --- | --- | --- |
| `cwnd` | Congestion Window | Bytes |
| `rtt` | RTT reportado pelo socket | Segundos |
| `inflight` | BytesInFlight | Bytes |
| `ssth` | Slow Start Threshold | Bytes |
| `rto` | Retransmission Timeout | Segundos |
| `next-tx` | Próximo número de sequência de transmissão | Sequence number |
| `next-rx` | Próximo número de sequência esperado na recepção | Sequence number |

Os traces de CWND, RTT e SSThresh registram o valor anterior na primeira chamada, associado ao instante inicial, e depois registram os novos valores nos eventos. O trace de BytesInFlight registra as mudanças observadas no atributo. Portanto, os arquivos representam eventos de alteração, não amostras periódicas em intervalos fixos.

A instrumentação usa os caminhos de trace do socket TCP, incluindo:

- `CongestionWindow`
- `SlowStartThreshold`
- `RTT`
- `RTO`
- `BytesInFlight`
- `NextTxSequence`
- `RxBuffer/NextRxSequence`

No cenário implementado, cada nó de origem possui o socket TCP usado pelo respectivo fluxo; o índice do arquivo de trace identifica esse fluxo de origem.

Quando `--flow_monitor=true`, também é produzido:

`CubicExperiment.flowmonitor`

Esse arquivo XML contém estatísticas por fluxo IP, como bytes e pacotes transmitidos/recebidos, perdas, soma dos atrasos, soma dos jitters e tempos do primeiro e último pacote recebido.

## 5. Automação das campanhas

### 5.1 Campanha inicial — 45 simulações

O script `scripts/cubic/run_scenarios.sh` executa a matriz inicial, com:

- 3 variantes: CUBIC, BBR e CUBIC-RTT;
- 3 atrasos de gargalo: 10, 50 e 100 ms;
- 5 repetições por combinação;
- 4 fluxos por simulação;
- 100 segundos por simulação.

Total: `3 × 3 × 5 = 45` simulações.

Os resultados são organizados por algoritmo, atraso e repetição:

```text
results/
|-- Cubic/atraso_<delay>/run_<n>/
|-- Bbr/atraso_<delay>/run_<n>/
\-- CubicRtt/atraso_<delay>/run_<n>/
```

### 5.2 Experimentos de parâmetros — 180 simulações

O script `run_parameter_experiments.sh` executa combinações adicionais de Alpha e Gamma para `TcpCubicRtt`.

A matriz do script contém 12 combinações de parâmetros, 3 atrasos e 5 repetições:

`12 × 3 × 5 = 180` simulações.

Os resultados são gravados em:

`results/parameter_experiments/<configuração>/<delay>ms/run_<n>/`

O script `scripts/cubic/analyze_parameter_experiments.py` processa essa campanha e grava seus arquivos consolidados em:

`results/parameter_experiments/consolidated/`

### 5.3 Campanha de robustez — 675 simulações

O script `run_robustness_experiments.sh` percorre três cenários de rede, quinze configurações de algoritmo/parâmetros, três atrasos e cinco repetições:

`3 × 15 × 3 × 5 = 675` simulações.

Cenários:

| Identificador | Gargalo | Fluxos | Atraso de acesso |
| --- | ---: | ---: | ---: |
| `bw1_f4` | 1 Mbps | 4 | 45 ms |
| `bw2_f8` | 2 Mbps | 8 | 45 ms |
| `access100` | 2 Mbps | 4 | 100 ms |

Os atrasos do gargalo são 10, 50 e 100 ms. A largura de banda de acesso é 10 Mbps e a duração de cada simulação é 100 segundos.

As quinze configurações são:

- CUBIC;
- BBR;
- CUBIC-RTT baseline (`Alpha=0.25`, `Gamma=0.05`);
- doze combinações adicionais de Alpha e Gamma, definidas no array `CONFIGS` do script.

A árvore de saída é:

```text
results/robustness_experiments/
|-- bw1_f4/
|   \-- <configuração>/<delay>ms/run_<n>/
|-- bw2_f8/
|   \-- <configuração>/<delay>ms/run_<n>/
|-- access100/
|   \-- <configuração>/<delay>ms/run_<n>/
\-- consolidated/
```

O script cria um arquivo `execution.log` em cada diretório de execução. Quando a simulação termina com sucesso e o arquivo FlowMonitor existe, cria também um marcador `DONE`. Ao ser executado novamente, pula uma execução que já possui `DONE` e FlowMonitor não vazio; isso permite retomar uma campanha sem repetir automaticamente os diretórios já concluídos.

O log geral da campanha é `robustness_execution.log`, na raiz do repositório.

## 6. Processamento dos dados

### 6.1 `analyze_results.py`

Esse módulo contém funções reutilizadas pelos demais scripts:

- leitura do XML do FlowMonitor;
- identificação dos fluxos TCP de dados;
- cálculo das métricas por fluxo;
- leitura dos arquivos `.data`;
- impressão de um resumo de uma execução individual.

O parser seleciona os fluxos de dados pelo classificador IPv4 e pela porta de destino configurada para o servidor. Os fluxos de retorno/ACK não são tratados como fluxos de dados da aplicação.

Para uma análise pontual, a interface do script é:

```bash
python3 scripts/cubic/analyze_results.py <algoritmo> <atraso_ms> <repetição>
```

Exemplo:

```bash
python3 scripts/cubic/analyze_results.py Cubic 10 1
```

### 6.2 `consolidate_results.py`

Esse script percorre a campanha inicial em `results/Cubic`, `results/Bbr` e `results/CubicRtt`. Para cada execução, lê o XML do FlowMonitor e os traces TCP associados aos fluxos.

Gera:

- `results/consolidated/resumo_simulacoes.csv`: uma linha por simulação;
- `results/consolidated/metricas_fluxos.csv`: uma linha por fluxo;
- `results/consolidated/relatorio_validacao.txt`: contagens esperadas/encontradas e ocorrências de validação.

**Atenção:** executar esse script reescreve os arquivos dentro de `results/consolidated/`. Ele não consolida a campanha de robustez.

### 6.3 `analyze_robustness_experiments.py`

Esse script percorre a estrutura da campanha de robustez, utiliza as funções de parsing e cálculo do módulo `consolidate_results.py`, e grava os resultados em:

`results/robustness_experiments/consolidated/`

Os arquivos gerados são:

- `resumo_simulacoes.csv`;
- `metricas_fluxos.csv`;
- `relatorio_validacao.txt`.

**Atenção:** essa consolidação é independente de `results/consolidated/`. As duas campanhas não devem ser misturadas nem sobrescritas umas pelas outras.

### 6.4 Tratamento dos traces na consolidação

O consolidator converte o RTT de segundos para milissegundos ao gerar as colunas de RTT dos CSVs. CWND, BytesInFlight e SSThresh permanecem em bytes.

O tratamento dos valores é específico por métrica:

- **CWND e RTT:** valores não positivos são desconsiderados no cálculo das estatísticas;
- **BytesInFlight:** zero é mantido, pois representa um estado válido sem dados em trânsito;
- **SSThresh:** zero e o valor sentinela `UINT32_MAX` são removidos das estatísticas numéricas; a ocorrência do sentinela é contabilizada separadamente.

Os arquivos brutos `.data` são mantidos como origem da informação. Os CSVs são produtos derivados e podem ser recriados a partir dos arquivos de cada campanha.

## 7. Métricas e campos consolidados

### 7.1 FlowMonitor

As métricas de rede são calculadas a partir dos contadores e tempos presentes no XML:

| Métrica | Como é obtida |
| --- | --- |
| TX/RX bytes | Contadores de bytes transmitidos e recebidos |
| TX/RX packets | Contadores de pacotes transmitidos e recebidos |
| Lost packets | Contador de pacotes perdidos reportado pelo FlowMonitor |
| Loss rate | `lost_packets / tx_packets × 100` |
| Throughput por fluxo | Bytes recebidos convertidos em bits, divididos pelo intervalo entre primeiro e último recebimento |
| Atraso médio | `delaySum / rxPackets` |
| Jitter médio | `jitterSum / (rxPackets - 1)`, quando há mais de um pacote recebido |
| Jain fairness | Calculado a partir das vazões dos fluxos incluídos na mesma simulação |

O throughput agregado da simulação usa o intervalo global entre o primeiro recebimento de qualquer fluxo e o último recebimento de qualquer fluxo. Por isso, não é obtido simplesmente somando os throughputs individuais.

### 7.2 Traces TCP

Para cada fluxo, os CSVs incluem estatísticas mínimo, máximo e média para CWND, RTT, BytesInFlight e SSThresh, além da quantidade de amostras disponível para cada métrica.

Os valores são estatísticas dos eventos registrados pelo trace. Como os traces são acionados por mudanças de estado, a média desses eventos não deve ser interpretada automaticamente como média temporal ponderada ao longo de toda a simulação.

## 8. Como preparar o ambiente

Clone o repositório incluindo o submodule:

```bash
git clone --recurse-submodules https://github.com/Gomez260/TCP_CUBIC-PerfomanceProposal.git
cd TCP_CUBIC-PerfomanceProposal
```

Se o repositório já foi clonado sem os submodules:

```bash
git submodule update --init --recursive
```

Entre no ns-3 e compile o experimento:

```bash
cd ns3/ns-3-dev-git
./ns3 build cubic-experiment
```

As dependências de compilação são as exigidas pela versão do ns-3 presente no submodule. Consulte a documentação dessa versão do ns-3 para instalar os pacotes necessários no sistema.

## 9. Executar uma simulação manual

A partir de `ns3/ns-3-dev-git`, crie o diretório de saída e execute:

```bash
mkdir -p ../../results/manual_test

./ns3 run "cubic-experiment --transport_prot=TcpCubic --num_flows=4 --bandwidth=2Mbps --delay=10ms --access_bandwidth=10Mbps --access_delay=45ms --duration=10 --tracing=true --flow_monitor=true --results_dir=../../results/manual_test --run=1"
```

Para executar CUBIC-RTT com parâmetros específicos, altere o protocolo e adicione os atributos:

```bash
./ns3 run "cubic-experiment --transport_prot=TcpCubicRtt --num_flows=4 --bandwidth=2Mbps --delay=10ms --access_bandwidth=10Mbps --access_delay=45ms --duration=10 --tracing=true --flow_monitor=true --results_dir=../../results/manual_test_rtt --run=1 --ns3::TcpCubicRtt::Alpha=0.25 --ns3::TcpCubicRtt::Gamma=0.05"
```

Para uma campanha completa, utilize os scripts de automação na raiz do repositório em vez de montar manualmente cada comando.

## 10. Comandos de processamento

Na raiz do repositório:

```bash
# Consolidar a campanha inicial (45 execuções)
python3 scripts/cubic/consolidate_results.py

# Consolidar a campanha de parâmetros Alpha/Gamma
python3 scripts/cubic/analyze_parameter_experiments.py

# Consolidar a campanha de robustez (675 execuções)
python3 scripts/cubic/analyze_robustness_experiments.py
```

Cada script lê uma estrutura de diretórios específica e escreve em seu próprio diretório de saída. Antes de executar uma consolidação, confira se os arquivos brutos da campanha correspondente estão presentes.

## 11. Relação entre as campanhas

As campanhas possuem objetivos operacionais e diretórios de entrada/saída distintos:

| Campanha | Execuções planejadas | Script de execução | Script de consolidação | Saída consolidada |
| --- | ---: | --- | --- | --- |
| Inicial | 45 | `scripts/cubic/run_scenarios.sh` | `scripts/cubic/consolidate_results.py` | `results/consolidated/` |
| Parâmetros | 180 | `run_parameter_experiments.sh` | `scripts/cubic/analyze_parameter_experiments.py` | `results/parameter_experiments/consolidated/` |
| Robustez | 675 | `run_robustness_experiments.sh` | `scripts/cubic/analyze_robustness_experiments.py` | `results/robustness_experiments/consolidated/` |

Não copie os CSVs de uma campanha para o diretório de outra. Cada consolidator procura entradas e grava saídas em caminhos próprios.

## 12. Referência rápida dos arquivos importantes

| Arquivo | Responsabilidade |
| --- | --- |
| `tcp-cubic-rtt.h/.cc` | Classe e lógica do TCP CUBIC-RTT |
| `cubic-experiment.cc` | Topologia, configuração da simulação, aplicações e traces |
| `run_scenarios.sh` | Execução da campanha inicial |
| `run_parameter_experiments.sh` | Execução das combinações adicionais de Alpha/Gamma |
| `run_robustness_experiments.sh` | Execução automatizada da campanha de robustez |
| `analyze_results.py` | Parser do FlowMonitor e leitor de traces |
| `consolidate_results.py` | Consolidação da campanha inicial e funções compartilhadas |
| `analyze_parameter_experiments.py` | Consolidação da campanha de parâmetros |
| `analyze_robustness_experiments.py` | Consolidação da campanha de robustez |

---

## Autor

Thales Gomes Batista

Ciência da Computação — Universidade Federal de Juiz de Fora (UFJF).
