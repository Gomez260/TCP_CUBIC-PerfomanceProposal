# Avaliação e Aprimoramento do TCP CUBIC Baseado em RTT

## 1. Introdução

Este projeto tem como objetivo estudar e avaliar o comportamento de diferentes algoritmos de controle de congestionamento TCP em redes com diferentes condições de atraso, tendo como foco principal a influência do **Round-Trip Time (RTT)** no desempenho da comunicação.

O estudo utiliza o **ns-3 (Network Simulator 3)** para realizar simulações controladas de redes e comparar o comportamento dos protocolos **TCP CUBIC** e **TCP BBR** em diferentes cenários de RTT.

Além da comparação entre protocolos existentes, o projeto propõe uma segunda etapa de desenvolvimento: a criação de uma **versão modificada do TCP CUBIC**, denominada neste projeto como **CUBIC-RTT**, incorporando um mecanismo baseado nas informações de RTT para modificar o comportamento do algoritmo original.

A proposta, portanto, não se limita a identificar qual protocolo apresenta melhor desempenho. O objetivo é investigar se uma modificação no comportamento do CUBIC baseada em RTT pode proporcionar melhorias em determinadas condições de rede.

---

## 2. Objetivo geral

Avaliar a influência do RTT no desempenho dos algoritmos TCP CUBIC e TCP BBR e investigar uma versão modificada do CUBIC que utilize informações de RTT em seu mecanismo de controle de congestionamento.

### Objetivos específicos

* Estudar o funcionamento do TCP CUBIC.
* Estudar o funcionamento do TCP BBR.
* Avaliar o comportamento dos protocolos sob diferentes valores de RTT.
* Coletar métricas de desempenho durante as simulações.
* Comparar o CUBIC original com o BBR.
* Desenvolver uma cópia do CUBIC original para servir como base para a proposta de modificação.
* Implementar um mecanismo baseado em RTT no CUBIC modificado.
* Comparar o CUBIC original, o CUBIC modificado e o BBR.
* Analisar se a modificação proposta apresenta benefícios em determinados cenários.

---

## 3. Hipótese da pesquisa

A hipótese do projeto é que o comportamento do TCP CUBIC pode ser aprimorado em determinadas condições de rede por meio da utilização explícita de informações relacionadas ao RTT durante seu processo de controle de congestionamento.

A proposta será avaliada experimentalmente por meio de simulações, permitindo verificar se o mecanismo baseado em RTT produz melhorias mensuráveis quando comparado ao CUBIC original.

---

# 4. Ambiente de simulação

O projeto utiliza o **ns-3** como ambiente de simulação.

A estrutura atual utiliza o exemplo:

```text
examples/tcp/tcp-variants-comparison.cc
```

Esse exemplo permite configurar diferentes parâmetros da rede e selecionar diferentes variantes de TCP para execução.

Entre os protocolos disponíveis está o:

```text
TcpCubic
TcpBbr
```

O projeto utilizará essa estrutura como base para os experimentos.

---

# 5. Estrutura geral do projeto

A metodologia será dividida em três implementações principais:

```text
                    Experimentos
                         │
             ┌───────────┼───────────┐
             │           │           │
             ▼           ▼           ▼
          CUBIC      CUBIC-RTT      BBR
         original    modificado
             │           │           │
             └───────────┼───────────┘
                         ▼
                    Comparação
                         │
                         ▼
                   Análise Python
```

### TCP CUBIC

Será utilizado como **baseline** do estudo.

O CUBIC original será mantido sem alterações para permitir uma comparação justa com a implementação modificada.

### TCP BBR

Será utilizado como protocolo de referência para comparação com o CUBIC.

### CUBIC-RTT

Será uma nova implementação baseada no CUBIC original.

A ideia é criar uma cópia da implementação existente do CUBIC e, posteriormente, modificar seu comportamento para incorporar a mecânica baseada em RTT proposta no projeto.

---

# 6. CUBIC modificado

A implementação modificada não substituirá o CUBIC original.

Será criada uma implementação independente, conceitualmente organizada da seguinte maneira:

```text
TcpCubic
├── tcp-cubic.cc
└── tcp-cubic.h

TcpCubicRTT
├── tcp-cubic-rtt.cc
└── tcp-cubic-rtt.h
```

Inicialmente, o CUBIC-RTT deverá possuir comportamento equivalente ao CUBIC original.

Depois disso, será introduzida a modificação relacionada ao RTT.

Essa abordagem permite preservar o algoritmo original e comparar diretamente:

```text
CUBIC original
       VS
CUBIC modificado
```

sem que alterações na implementação original prejudiquem o baseline experimental.

---

# 7. Papel do tcp-variants-comparison.cc

O arquivo:

```text
tcp-variants-comparison.cc
```

será utilizado principalmente para **configurar e executar os experimentos**.

Ele será responsável por definir características como:

* protocolo TCP utilizado;
* largura de banda;
* atraso;
* número de fluxos;
* duração da simulação;
* taxa de erro;
* tamanho da MTU;
* mecanismo de recuperação;
* fila;
* tracing;
* Flow Monitor;
* nome dos arquivos de saída.

A lógica principal do algoritmo CUBIC-RTT, entretanto, ficará na implementação do próprio protocolo.

Conceitualmente:

```text
tcp-variants-comparison.cc
            │
            │ seleciona protocolo
            ▼
      TcpCubicRTT
            │
            │ executa algoritmo
            ▼
      Controle TCP modificado
```

Assim, o arquivo de comparação funciona como o **ambiente experimental**, enquanto a implementação do CUBIC-RTT contém a contribuição proposta.

---

# 8. Metodologia experimental

Os experimentos serão organizados a partir da variação do RTT.

A ideia é executar os mesmos cenários para diferentes valores de RTT, permitindo observar como o aumento do atraso influencia o comportamento dos protocolos.

Para cada cenário serão executados, inicialmente:

```text
CUBIC
CUBIC-RTT
BBR
```

A comparação será realizada mantendo as demais condições da rede equivalentes.

Exemplo conceitual:

```text
RTT X
├── CUBIC
├── CUBIC-RTT
└── BBR

RTT Y
├── CUBIC
├── CUBIC-RTT
└── BBR

RTT Z
├── CUBIC
├── CUBIC-RTT
└── BBR
```

Os valores exatos de RTT e os demais parâmetros do cenário serão definidos na etapa de planejamento experimental.

---

# 9. Métricas de avaliação

Nem todos os arquivos gerados pelo ns-3 terão a mesma importância para a análise.

As principais métricas previstas são:

## 9.1 Congestion Window — `cwnd.data`

A janela de congestionamento será uma das principais métricas do projeto.

Ela permitirá observar como cada algoritmo reage às condições da rede e como o CUBIC-RTT se comporta em relação ao CUBIC original.

Será possível analisar, por exemplo:

* crescimento da janela;
* redução após eventos de congestionamento;
* estabilidade;
* comportamento durante diferentes RTTs.

---

## 9.2 RTT — `rtt.data`

O arquivo de RTT será utilizado para acompanhar o comportamento do atraso observado durante a transmissão.

Essa métrica é especialmente importante porque o RTT é a principal variável investigada no projeto.

---

## 9.3 In-flight — `inflight.data`

O número de dados em trânsito será utilizado como métrica complementar.

Essa informação pode ajudar a compreender como CUBIC, CUBIC-RTT e BBR utilizam a capacidade da rede.

---

## 9.4 Throughput

O throughput será uma das principais métricas de desempenho.

Ele permitirá responder perguntas como:

> O CUBIC-RTT consegue transmitir mais dados por segundo que o CUBIC original em determinados valores de RTT?

O throughput poderá ser obtido a partir dos dados coletados pelo Flow Monitor.

---

## 9.5 Perda de pacotes

A quantidade de pacotes perdidos poderá ser utilizada para avaliar o comportamento dos protocolos em cenários com perdas.

Essa métrica também permitirá investigar se uma eventual melhoria de throughput ocorre às custas de um aumento significativo de perdas.

---

## 9.6 Atraso

Os dados do Flow Monitor poderão ser utilizados para complementar a análise do comportamento dos protocolos em relação ao atraso.

---

# 10. Arquivos `.data`

O ns-3 pode gerar diversos arquivos durante uma execução com tracing habilitado.

Entre eles:

```text
cwnd.data
rtt.data
inflight.data
ssth.data
rto.data
next-tx.data
next-rx.data
```

Os arquivos mais importantes inicialmente serão:

```text
cwnd.data
rtt.data
inflight.data
```

Além dos dados provenientes do:

```text
.flowmonitor
```

Os demais arquivos poderão ser utilizados como informações auxiliares caso sejam relevantes para alguma análise específica.

### Prioridade inicial

| Arquivo         | Prioridade |
| --------------- | ---------- |
| `cwnd.data`     | Alta       |
| `rtt.data`      | Alta       |
| `inflight.data` | Alta       |
| `.flowmonitor`  | Alta       |
| `ssth.data`     | Média      |
| `rto.data`      | Média      |
| `next-tx.data`  | Baixa      |
| `next-rx.data`  | Baixa      |

Essa seleção poderá ser ajustada após os primeiros experimentos.

---

# 11. Organização dos resultados

Os resultados das simulações serão armazenados em arquivos gerados pelo ns-3.

Para evitar sobrescrita dos resultados, cada protocolo poderá utilizar um prefixo diferente.

Exemplo:

```bash
./ns3 run "tcp-variants-comparison --transport_prot=TcpCubic --tracing=true --flow_monitor=true --prefix_name=Cubic"
```

```bash
./ns3 run "tcp-variants-comparison --transport_prot=TcpBbr --tracing=true --flow_monitor=true --prefix_name=Bbr"
```

Posteriormente, o CUBIC modificado poderá utilizar, por exemplo:

```text
CubicRTT
```

A organização deverá permitir identificar facilmente:

```text
protocolo
RTT
cenário
execução
```

---

# 12. Análise utilizando Python

O ns-3 será responsável pela **simulação e geração dos dados**.

O Python será utilizado posteriormente para o processamento e visualização dos resultados.

A arquitetura será:

```text
              ns-3 / C++
                   │
                   ▼
             Simulações
                   │
                   ▼
          Arquivos de dados
                   │
       ┌───────────┴───────────┐
       │                       │
    *.data                *.flowmonitor
       │                       │
       └───────────┬───────────┘
                   ▼
                 Python
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
       Gráficos  Métricas  Tabelas
```

O Python poderá ser utilizado para:

* leitura dos arquivos `.data`;
* processamento dos resultados;
* cálculo de métricas;
* geração de gráficos;
* comparação entre protocolos;
* organização dos resultados;
* análise estatística posteriormente, se necessário.

---

# 13. Automação dos experimentos

Após a definição completa da metodologia, será avaliada a criação de uma forma de automatizar a execução das simulações.

A ideia é evitar a execução manual de cada cenário.

Em vez de executar individualmente:

```text
CUBIC + RTT A
CUBIC + RTT B
CUBIC + RTT C

CUBIC-RTT + RTT A
CUBIC-RTT + RTT B
CUBIC-RTT + RTT C

BBR + RTT A
BBR + RTT B
BBR + RTT C
```

um programa/controlador poderá executar automaticamente todas as combinações definidas.

A automação será implementada somente após a definição da matriz experimental.

---

# 14. Fluxo completo do projeto

O fluxo planejado é:

```text
              Definição dos cenários
                       │
                       ▼
              Configuração do ns-3
                       │
                       ▼
             Execução das simulações
                       │
                       ▼
               Geração dos dados
                       │
              ┌────────┴────────┐
              ▼                 ▼
           *.data          *.flowmonitor
              │                 │
              └────────┬────────┘
                       ▼
                    Python
                       │
                       ▼
              Processamento
                       │
                       ▼
               Gráficos/tabelas
                       │
                       ▼
                  Comparação
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
      CUBIC         CUBIC-RTT         BBR
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 Análise final
```

---

# 15. Comparação final

A principal comparação proposta será:

### CUBIC original × CUBIC-RTT

Objetivo:

> Verificar se a utilização da mecânica baseada em RTT proporciona melhoria em relação ao comportamento original do CUBIC.

### CUBIC × BBR

Objetivo:

> Utilizar o BBR como referência para avaliar o desempenho do CUBIC em diferentes condições de RTT.

### CUBIC-RTT × BBR

Objetivo:

> Verificar se a proposta modificada consegue apresentar desempenho competitivo em relação ao BBR.

---

# 16. Questão central da pesquisa

A investigação pode ser resumida pela seguinte questão:

> **Como a utilização de informações de RTT na tomada de decisões do TCP CUBIC pode influenciar seu desempenho em diferentes condições de rede?**

A partir dela, os experimentos buscarão avaliar se o CUBIC-RTT apresenta melhorias em métricas como:

* throughput;
* RTT;
* congestion window;
* dados em trânsito;
* perdas de pacotes;
* atraso.

---

# 17. Estado atual do projeto

### Concluído

* [x] Ambiente ns-3 configurado.
* [x] Execução do `tcp-variants-comparison` funcionando.
* [x] Execução do TCP CUBIC.
* [x] Execução do TCP BBR.
* [x] Habilitação de tracing.
* [x] Habilitação do Flow Monitor.
* [x] Geração dos arquivos `.data`.
* [x] Identificação das principais métricas disponíveis.
* [x] Definição inicial da utilização do Python para análise.

### Em planejamento

* [ ] Definir exatamente os valores de RTT.
* [ ] Definir todos os parâmetros dos cenários.
* [ ] Definir a matriz completa de experimentos.
* [ ] Definir as métricas finais que serão utilizadas.
* [ ] Definir exatamente a mecânica baseada em RTT.
* [ ] Criar o CUBIC-RTT a partir do CUBIC original.
* [ ] Implementar a modificação proposta.
* [ ] Validar o CUBIC-RTT contra o CUBIC original.
* [ ] Automatizar as simulações.
* [ ] Desenvolver os scripts de análise em Python.
* [ ] Gerar gráficos e tabelas.
* [ ] Analisar os resultados.

---

# 18. Princípio da implementação

A implementação seguirá inicialmente uma abordagem conservadora:

1. Preservar o CUBIC original.
2. Criar uma cópia independente.
3. Validar que a cópia apresenta comportamento equivalente ao CUBIC original.
4. Implementar a mecânica baseada em RTT.
5. Executar novamente os mesmos experimentos.
6. Comparar CUBIC, CUBIC-RTT e BBR.
7. Avaliar quantitativamente os resultados.

Dessa forma, qualquer diferença observada entre o CUBIC original e o CUBIC-RTT poderá ser associada à alteração proposta, mantendo um **baseline experimental claro**.

---

## 19. Tecnologias

* **C++** — implementação e execução das simulações no ns-3.
* **ns-3** — ambiente de simulação de redes.
* **TCP CUBIC** — algoritmo de congestionamento utilizado como baseline.
* **TCP BBR** — algoritmo utilizado como referência.
* **Python** — processamento, análise e visualização dos resultados.
* **Flow Monitor** — coleta de métricas dos fluxos.

---

## 20. Próximo passo

Antes da implementação do CUBIC-RTT e da automação, será definida a **matriz experimental completa**, incluindo:

* valores de RTT;
* largura de banda;
* atraso dos enlaces;
* número de fluxos;
* duração das simulações;
* presença ou ausência de perdas;
* tipo de fila;
* métricas coletadas;
* quantidade de repetições de cada experimento.

Somente após essa definição será iniciada a implementação definitiva da proposta.
