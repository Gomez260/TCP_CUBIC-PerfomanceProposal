#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$HOME/TCP_CUBIC-PerfomanceProposal"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"
RESULTS_DIR="$PROJECT_DIR/results/parameter_experiments"
LOG_FILE="$RESULTS_DIR/parameter_campaign.log"

# Grade fatorial balanceada 3x3; baseline definido antes da análise.
NUM_REPETITIONS=5
NUM_FLOWS=4
BANDWIDTH="2Mbps"
ACCESS_BANDWIDTH="10Mbps"
ACCESS_DELAY="45ms"
DURATION=100
DELAYS=(10 50 100)
ALPHAS=(0.10 0.25 0.50)
GAMMAS=(0.00 0.05 0.10)

cd "$NS3_DIR" || {
    echo "ERRO: ns-3 não encontrado em $NS3_DIR"
    exit 1
}

mkdir -p "$RESULTS_DIR"

EXPECTED=135
EXECUTED=0
SKIPPED=0
FAILED=0

{
    echo "CAMPANHA DE SENSIBILIDADE CUBIC-RTT"
    echo "Baseline pré-definida: Alpha=0.25, Gamma=0.05"
    echo "Grade: Alpha=(0.10, 0.25, 0.50), Gamma=(0.00, 0.05, 0.10)"
    echo "Repetições configuradas: $NUM_REPETITIONS"
    echo "Duração por execução: $DURATION s"
    echo "Total planejado: $EXPECTED"
    echo "ATENÇÃO: --run sozinho não comprova aleatoriedade."
    echo "Não interpretar estas repetições como independentes até validar fontes aleatórias no simulador."

    for alpha in "${ALPHAS[@]}"; do
        for gamma in "${GAMMAS[@]}"; do
            experiment="A${alpha}_G${gamma}"

            for delay in "${DELAYS[@]}"; do
                for run in $(seq 1 "$NUM_REPETITIONS"); do
                    run_dir="$RESULTS_DIR/$experiment/${delay}ms/run_$run"
                    flowmonitor="$run_dir/CubicExperiment.flowmonitor"
                    mkdir -p "$run_dir"

                    # Nunca sobrescrever uma execução que já possui FlowMonitor.
                    if [[ -s "$flowmonitor" ]]; then
                        echo "[PULANDO - resultado já existe] $experiment/${delay}ms/run_$run"
                        SKIPPED=$((SKIPPED + 1))
                        continue
                    fi

                    echo "[EXECUTANDO] $experiment | gargalo=${delay}ms | run=$run"
                    if ./ns3 run "cubic-experiment \
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
                        --ns3::TcpCubicRtt::Gamma=$gamma" > "$run_dir/execution.log" 2>&1 \
                        && [[ -s "$flowmonitor" ]]; then
                        EXECUTED=$((EXECUTED + 1))
                        echo "[OK] $experiment/${delay}ms/run_$run"
                    else
                        FAILED=$((FAILED + 1))
                        echo "[FALHA] $experiment/${delay}ms/run_$run - consulte $run_dir/execution.log"
                    fi
                    echo "executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED"
                done
            done
        done
    done

    echo "FIM | executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED planejadas=$EXPECTED"
} 2>&1 | tee -a "$LOG_FILE"

if (( FAILED > 0 )); then
    exit 1
fi
