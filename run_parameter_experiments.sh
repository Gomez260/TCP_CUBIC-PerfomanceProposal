#!/bin/bash
set -euo pipefail

NS3_DIR="$HOME/TCP_CUBIC-PerfomanceProposal/ns3/ns-3-dev-git"
RESULTS_DIR="$HOME/TCP_CUBIC-PerfomanceProposal/results/parameter_experiments"

NUM_REPETITIONS=5
NUM_FLOWS=4
BANDWIDTH="2Mbps"
ACCESS_BANDWIDTH="10Mbps"
ACCESS_DELAY="45ms"
DURATION=100

DELAYS=(10 50 100)

# Somente combinacoes ainda nao executadas.
CONFIGS=(
    "0.10 0.00"
    "0.10 0.025"
    "0.10 0.05"
    "0.10 0.10"

    "0.25 0.00"
    "0.25 0.025"

    "0.50 0.00"
    "0.50 0.025"

    "0.75 0.00"
    "0.75 0.025"
    "0.75 0.05"
    "0.75 0.10"
)

cd "$NS3_DIR" || exit 1
mkdir -p "$RESULTS_DIR"

TOTAL=0

echo "============================================"
echo "EXPERIMENTOS DE ALPHA E GAMMA - TCP CUBIC RTT"
echo "============================================"
echo "Configuracoes novas: ${#CONFIGS[@]}"
echo "Atrasos: ${DELAYS[*]} ms"
echo "Repeticoes: $NUM_REPETITIONS"
echo

for config in "${CONFIGS[@]}"; do
    read -r alpha gamma <<< "$config"

    experiment="A${alpha}_G${gamma}"

    echo
    echo "############################################"
    echo "Configuracao: $experiment"
    echo "Alpha=$alpha | Gamma=$gamma"
    echo "############################################"

    for delay in "${DELAYS[@]}"; do
        for run in $(seq 1 "$NUM_REPETITIONS"); do

            run_dir="$RESULTS_DIR/$experiment/${delay}ms/run_$run"
            mkdir -p "$run_dir"

            echo
            echo "Executando $experiment | ${delay}ms | run $run"

            ./ns3 run "cubic-experiment \
                --transport_prot=TcpCubicRtt \
                --num_flows=$NUM_FLOWS \
                --bandwidth=$BANDWIDTH \
                --delay=${delay}ms \
                --access_bandwidth=$ACCESS_BANDWIDTH \
                --access_delay=$ACCESS_DELAY \
                --duration=$DURATION \
                --tracing=true \
                --flow_monitor=true \
                --results_dir=$run_dir \
                --run=$run \
                --ns3::TcpCubicRtt::Alpha=$alpha \
                --ns3::TcpCubicRtt::Gamma=$gamma"

            TOTAL=$((TOTAL + 1))
        done
    done
done

echo
echo "============================================"
echo "BATERIA EXPERIMENTAL CONCLUIDA"
echo "Simulacoes executadas: $TOTAL"
echo "Esperado: 180"
echo "Resultados: $RESULTS_DIR"
echo "============================================"
