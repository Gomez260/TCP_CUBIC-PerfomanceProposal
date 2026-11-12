# Experimento: adaptação pelo aumento relativo do RTT

Esta branch contém o instalador da alteração experimental para o submodule ns-3.

## Hipótese

Além da adaptação já existente em função de RTT mínimo / RTT de referência, usar o aumento relativo do RTT observado durante a conexão:

```
relativeIncrease = clamp((RTT_sample - RTT_min) / RTT_min, 0, 1)
```

O sinal é suavizado por EWMA:
```
EWMA_n = 0.9 * EWMA_(n-1) + 0.1 * relativeIncrease_n
```

O sinal não tem unidade e permite comparar aumentos relativos entre caminhos com RTTs mínimos diferentes.

## Como ele influencia os parâmetros

- C: `C_base / (1 + Alpha * EWMA)`. Quando o RTT cresce proporcionalmente, o crescimento cúbico fica mais conservador.
- Beta permanece com a adaptação original por RTT mínimo/referência. Não o alteramos nesta primeira hipótese, para isolar o efeito da nova variável sobre o crescimento da janela.
- O EWMA é reiniciado em `CubicReset()`, evitando carregar o sinal de uma época anterior à perda.

Com Alpha=0.25 e EWMA=1, o fator adicional reduz C em 20% em relação ao C adaptativo-base. O sinal é limitado a [0,1].

## Aplicação local no submodule

A integração do GitHub não tem permissão de escrita no repositório independente `Gomez260/ns-3-dev-git`. Por isso, esta branch do repositório principal contém um script que aplica as mudanças no clone local do submodule:

```bash
python3 scripts/cubic/apply_relative_rtt_adaptation.py
```

Depois de executar, revisar obrigatoriamente:

```bash
cd ns3/ns-3-dev-git
git diff -- src/internet/model/tcp-cubic-rtt.cc src/internet/model/tcp-cubic-rtt.h
./ns3 build
```

A alteração ainda é uma hipótese experimental: não há alegação de melhora de throughput ou Jain fairness até executar e analisar os experimentos. Não executar as campanhas de 180 ou 675 simulações nesta etapa.
