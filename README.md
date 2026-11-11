# TCP CUBIC-RTT — Avaliação de um mecanismo de controle de congestionamento baseado em RTT

> Projeto de pesquisa desenvolvido como Trabalho de Conclusão de Curso (TCC), utilizando o **ns-3** para investigar o comportamento do TCP CUBIC e avaliar uma proposta de modificação que incorpora informações de Round-Trip Time (RTT) ao controle de congestionamento.

## Visão geral

O TCP CUBIC é um algoritmo de controle de congestionamento amplamente utilizado. Este projeto investiga como seu comportamento pode ser influenciado pela utilização explícita de informações de RTT.

A proposta consiste em desenvolver e avaliar uma variante experimental denominada **TCP CUBIC-RTT**, mantendo o TCP CUBIC original como baseline. O TCP BBR também é utilizado como referência comparativa.

O estudo utiliza simulações no **ns-3** para comparar os algoritmos sob diferentes condições de rede, observando tanto métricas de desempenho fim a fim quanto variáveis internas do controle de congestionamento.

**Algoritmos avaliados:**

- **TCP CUBIC:** implementação original, utilizada como baseline.
- **TCP CUBIC-RTT:** variante experimental derivada do CUBIC, com mecanismo de ajuste baseado em RTT.
- **TCP BBR:** algoritmo de referência para comparação.

O objetivo não é pressupor que a modificação seja superior, mas verificar experimentalmente em quais condições — se houver — ela apresenta benefícios e quais possíveis custos estão associados.

## Pergunta de pesquisa

**Como a utilização de informações de RTT nas decisões do TCP CUBIC influencia seu desempenho em diferentes condições de rede?**

A investigação considera aspectos como utilização da capacidade do enlace, estabilidade, justiça entre fluxos, atraso e perdas de pacotes.

## Arquitetura experimental

As simulações são executadas no ns-3, com um cenário de gargalo entre dois gateways. Os fluxos TCP atravessam os enlaces de acesso e compartilham o enlace de gargalo.

A topologia permite variar parâmetros como:

- largura de banda do gargalo;
- atraso do enlace de gargalo;
- atraso dos enlaces de acesso;
- quantidade de fluxos concorrentes;
- algoritmo TCP utilizado;
- parâmetros da proposta CUBIC-RTT;
- número de repetições.

Os experimentos utilizam condições equivalentes entre algoritmos dentro de cada configuração, de modo a permitir comparações controladas.

### Matriz de experimentos

A campanha de robustez já executada contém **675 simulações**, organizadas em:

- 3 cenários de rede;
- 15 configurações de algoritmo/parâmetros por cenário;
- 5 repetições por configuração.

Os cenários incluem variações na largura de banda do gargalo, no número de fluxos e no atraso dos enlaces de acesso. Os atrasos do gargalo também são variados.

| Cenário | Largura de banda do gargalo | Fluxos | Atraso de acesso |
| --- | ---: | ---: | ---: |
| `bw1_f4` | 1 Mbps | 4 | 45 ms |
| `bw2_f8` | 2 Mbps | 8 | 45 ms |
| `access100` | 2 Mbps | 4 | 100 ms |

Os atrasos do gargalo avaliados são 10 ms, 50 ms e 100 ms. A largura de banda dos enlaces de acesso é de 10 Mbps e a duração configurada para a campanha é de 100 segundos por simulação.

A matriz inclui CUBIC, BBR, uma configuração baseline de CUBIC-RTT e diferentes combinações dos parâmetros Alpha e Gamma da proposta. Os valores específicos são definidos nos scripts da campanha.

> A campanha de 675 simulações é distinta dos experimentos iniciais de 45 simulações. Seus resultados são armazenados em diretórios separados para evitar mistura entre conjuntos experimentais.

## Métricas coletadas

A avaliação combina métricas do **FlowMonitor** com traces internos dos sockets TCP.

### Métricas principais — FlowMonitor

| Métrica | O que permite avaliar |
| --- | --- |
| Throughput | Taxa efetiva de dados recebidos |
| Taxa de perda | Proporção de pacotes transmitidos que foram perdidos |
| Atraso médio | Tempo médio de entrega dos pacotes |
| Jitter médio | Variação do atraso entre pacotes |
| Jain's Fairness Index | Distribuição da vazão entre os fluxos concorrentes |

Essas métricas são utilizadas para comparar o desempenho fim a fim dos algoritmos.

### Métricas complementares — traces TCP

| Trace | Unidade | Finalidade |
| --- | --- | --- |
| CWND (`cwnd.data`) | Bytes | Acompanhar a evolução da janela de congestionamento |
| RTT (`rtt.data`) | Segundos no arquivo bruto; convertido para ms na análise | Observar a evolução do RTT registrado pelo socket |
| Bytes in Flight (`inflight.data`) | Bytes | Acompanhar a quantidade de dados em trânsito |
| Slow Start Threshold (`ssth.data`) | Bytes | Observar as alterações do limiar de slow start |

Os traces ajudam a interpretar **como** os algoritmos se comportam internamente e complementam as métricas de desempenho do FlowMonitor. Eles não substituem as métricas principais.

Valores especiais de inicialização do ns-3, como `UINT32_MAX` em SSThresh, são tratados separadamente na consolidação para não distorcer estatísticas como mínimo, máximo e média. O valor zero de BytesInFlight é preservado, pois representa um estado válido.

## Implementação da proposta

O TCP CUBIC original é mantido separado da implementação modificada. A variante CUBIC-RTT deriva do CUBIC e incorpora a lógica experimental baseada em RTT.

Essa separação permite:

1. preservar o algoritmo original como baseline;
2. modificar a variante experimental sem alterar o CUBIC de referência;
3. executar os algoritmos sob a mesma infraestrutura de simulação;
4. comparar seus resultados sob as mesmas condições de rede.

A implementação do mecanismo proposto está no código do ns-3 integrado ao repositório. Os detalhes matemáticos e os parâmetros do mecanismo devem ser consultados diretamente no código-fonte e na documentação da pesquisa, evitando tratar a hipótese de melhoria como um resultado já comprovado.

## Estrutura do repositório

A organização principal do projeto é:

```text
TCP_CUBIC-PerfomanceProposal/
├── ns3/
│   └── ns-3-dev-git/              # Código-fonte e ambiente de simulação ns-3
│       ├── src/internet/          # Implementações dos algoritmos TCP
│       └── examples/tcp/          # Experimento cubic-experiment
├── scripts/
│   └── cubic/
│       ├── analyze_results.py
│       ├── consolidate_results.py
│       ├── analyze_robustness_experiments.py
│       └── ...                    # Scripts de execução e análise
├── results/
│   ├── Cubic/                     # Resultados dos experimentos iniciais
│   ├── CubicRtt/
│   ├── Bbr/
│   ├── consolidated/              # Consolidação dos experimentos iniciais
│   └── robustness_experiments/
│       └── consolidated/          # Consolidação da campanha de robustez
└── README.md
```

A árvore acima destaca os diretórios centrais do projeto; arquivos auxiliares e subdiretórios de resultados podem variar conforme as campanhas executadas.

## Execução de uma simulação

O experimento utilizado é o `cubic-experiment`, localizado em `examples/tcp/` dentro do ns-3.

Exemplo de execução de uma simulação com TCP CUBIC:

```bash
cd ns3/ns-3-dev-git

./ns3 run "cubic-experiment --transport_prot=TcpCubic --num_flows=4 --bandwidth=2Mbps --delay=10ms --access_bandwidth=10Mbps --access_delay=45ms --duration=100 --tracing=true --flow_monitor=true --results_dir=../../results/cubic/cenario01"
```

O diretório indicado em `--results_dir` deve existir antes da execução:

```bash
mkdir -p ../../results/cubic/cenario01
```

Para executar outra variante, altere o parâmetro `--transport_prot` conforme o identificador registrado no ns-3. Os parâmetros Alpha e Gamma da variante CUBIC-RTT também podem ser configurados no experimento.

## Automação e análise

O projeto possui scripts em `scripts/cubic/` para automatizar campanhas, processar traces e consolidar os dados do FlowMonitor.

As etapas gerais são:

1. configurar a matriz experimental;
2. executar as simulações no ns-3;
3. armazenar os arquivos brutos de cada execução;
4. extrair as métricas do FlowMonitor;
5. processar os traces TCP por fluxo;
6. consolidar os resultados em CSV;
7. validar a consistência dos dados;
8. gerar análises e gráficos para comparação.

Os principais arquivos de análise incluem:

- `analyze_results.py`: leitura e extração de dados dos resultados;
- `consolidate_results.py`: consolidação dos experimentos iniciais;
- `analyze_robustness_experiments.py`: análise da campanha de robustez.

Os CSVs consolidados incluem um resumo por simulação e métricas individualizadas por fluxo. Os relatórios de validação registram a quantidade de simulações e fluxos processados e eventuais inconsistências estruturais.

## Resultados e organização dos dados

Os dados brutos são mantidos separados dos arquivos consolidados. Essa separação facilita a reprodução das análises sem precisar executar novamente as simulações.

| Diretório | Conteúdo |
| --- | --- |
| `results/consolidated/` | Consolidação dos experimentos iniciais (45 simulações) |
| `results/robustness_experiments/` | Dados brutos da campanha de robustez |
| `results/robustness_experiments/consolidated/` | Consolidação da campanha de robustez (675 simulações) |

Os resultados consolidados devem sempre ser interpretados considerando a versão da instrumentação e dos scripts utilizada para produzi-los. Em particular, alterações recentes nos callbacks dos traces exigem novas execuções para que as métricas internas de CWND, RTT, InFlight e SSThresh representem a instrumentação corrigida.

**Não há, neste README, uma conclusão de superioridade do CUBIC-RTT.** Essa conclusão depende da análise comparativa e estatística dos resultados experimentais.

## Estado atual do projeto

### Implementado e executado

- [x] Ambiente ns-3 integrado ao projeto.
- [x] Implementação experimental `TcpCubicRtt`.
- [x] Experimento próprio `cubic-experiment`.
- [x] Topologia com dois gateways e enlace de gargalo.
- [x] Execução de CUBIC, CUBIC-RTT e BBR.
- [x] Coleta de métricas do FlowMonitor.
- [x] Instrumentação de CWND, RTT, BytesInFlight e SSThresh.
- [x] Automação e execução da campanha de robustez de 675 simulações.
- [x] Consolidação dos resultados da campanha de robustez.
- [x] Validação estrutural dos CSVs e consistência de métricas agregadas e por fluxo.
- [x] Correção dos callbacks para que cada trace registre sua própria métrica, sem escrita cruzada entre CWND e SSThresh.
- [x] Ajustes no processamento de BytesInFlight e do valor sentinela de SSThresh.
- [x] Compilação e execução de uma simulação curta para verificar a geração dos traces após as alterações.

### Em andamento

- [ ] Executar uma nova bateria com a instrumentação corrigida.
- [ ] Consolidar novamente os traces gerados pela instrumentação atualizada.
- [ ] Comparar os resultados de desempenho e comportamento interno dos algoritmos.
- [ ] Produzir gráficos e tabelas finais.
- [ ] Realizar a análise estatística e discutir limitações dos experimentos.
- [ ] Documentar a formulação completa e a justificativa dos parâmetros da proposta CUBIC-RTT.

## Tecnologias

- **C++:** implementação dos algoritmos e dos experimentos.
- **ns-3:** simulador de redes utilizado nos experimentos.
- **Python:** automação, processamento e análise dos resultados.
- **TCP CUBIC / CUBIC-RTT / BBR:** algoritmos comparados.
- **FlowMonitor:** coleta de métricas dos fluxos.

## Escopo e reprodutibilidade

Este repositório reúne o código da proposta, a configuração dos experimentos e os scripts utilizados para processar os resultados. Para reproduzir uma campanha, é importante registrar:

- versão/commit do ns-3 utilizado;
- versão do código dos algoritmos;
- parâmetros de cada cenário;
- parâmetros Alpha e Gamma;
- duração e quantidade de repetições;
- scripts utilizados na execução e consolidação.

Como os resultados dependem da versão do código e da instrumentação, novas campanhas devem ser armazenadas em diretórios próprios, sem sobrescrever os dados de campanhas anteriores.

---

## Autor

**Thales Gomes Batista**

Projeto acadêmico desenvolvido no contexto do curso de Ciência da Computação — Universidade Federal de Juiz de Fora (UFJF).
