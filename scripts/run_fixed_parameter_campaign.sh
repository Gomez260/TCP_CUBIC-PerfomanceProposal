
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/TCP_CUBIC-PerfomanceProposal}"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"

# Pasta separada para preservar os resultados anteriores de 300 segundos.
RESULTS_DIR="$PROJECT_DIR/results/campaign_60s_reduced"

REPETITIONS="${REPETITIONS:-3}"

NUM_FLOWS=4
ACCESS_BANDWIDTH="${ACCESS_BANDWIDTH:-1Gbps}"
WARMUP=20
DURATION=60
RANDOM_START_MAX=2
QUEUE_BDP=1

ALPHA_ADAPTIVE="${ALPHA_ADAPTIVE:-0.25}"
GAMMA_ADAPTIVE="${GAMMA_ADAPTIVE:-0.05}"

if ! [[ "$REPETITIONS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERRO: REPETITIONS deve ser um inteiro positivo (atual: $REPETITIONS)" >&2
    exit 1
fi

declare -A ACCESS_PROFILES=(
    [low]="5ms,10ms,15ms,20ms"
    [heterogeneous]="10ms,30ms,60ms,90ms"
    [high]="30ms,60ms,90ms,120ms"
)

declare -A PROTOCOLS=(
    [cubic]="TcpCubic"
    [adaptive]="TcpCubicRtt"
    [fixed]="TcpCubicRtt"
)

# Quatro cenarios selecionados:
# Low: 10 Mbps/10 ms e 100 Mbps/100 ms
# Heterogeneous: 10 Mbps/100 ms e 100 Mbps/10 ms
SCENARIOS=(
    "low|10Mbps|10"
    "low|100Mbps|100"
    "heterogeneous|10Mbps|100"
    "heterogeneous|100Mbps|10"
)

cd "$NS3_DIR" || {
    echo "ERRO: ns-3 nao encontrado em $NS3_DIR" >&2
    exit 1
}

mkdir -p "$RESULTS_DIR"

EXPECTED=$((
    ${#SCENARIOS[@]} *
    ${#PROTOCOLS[@]} *
    REPETITIONS
))

EXECUTED=0
SKIPPED=0
FAILED=0
TASKS=()

echo "CAMPANHA REDUZIDA: CUBIC ORIGINAL x CUBIC-RTT ADAPTATIVO x FIXO"
echo "Adaptativo: Alpha=$ALPHA_ADAPTIVE Gamma=$GAMMA_ADAPTIVE"
echo "Fixo: Alpha=0 Gamma=0"
echo "Cenarios selecionados: ${#SCENARIOS[@]}"
echo "Repeticoes: $REPETITIONS"
echo "Fluxos TCP: $NUM_FLOWS"
echo "Warmup: ${WARMUP}s | medicao: ${DURATION}s"
echo "Concorrencia: 1 simulacao por vez"
echo "Resultados: $RESULTS_DIR"
echo "Total planejado: $EXPECTED"

# Primeiro identifica resultados ja concluidos e prepara a fila.
for scenario in "${SCENARIOS[@]}"; do
    IFS='|' read -r profile bandwidth delay <<< "$scenario"

    access_delays="${ACCESS_PROFILES[$profile]}"

    for mode in cubic adaptive fixed; do
        protocol="${PROTOCOLS[$mode]}"

        for run in $(seq 1 "$REPETITIONS"); do
            run_dir="$RESULTS_DIR/$profile/$bandwidth/${delay}ms/$mode/run_$run"
            flowmonitor="$run_dir/CubicExperiment.flowmonitor"

            mkdir -p "$run_dir"

            if [[ -f "$run_dir/DONE" && -s "$flowmonitor" ]] &&
               python3 -c 'import sys, xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' "$flowmonitor" >/dev/null 2>&1; then

                echo "[PULANDO] $profile/$bandwidth/${delay}ms/$mode/run_$run"
                SKIPPED=$((SKIPPED + 1))
            else
                rm -f "$run_dir/DONE" "$flowmonitor"

                TASKS+=("$profile|$bandwidth|$delay|$mode|$run|$protocol|$access_delays|$run_dir")
            fi
        done
    done
done

echo "Pendentes: ${#TASKS[@]} | ja concluidas: $SKIPPED"

if (( ${#TASKS[@]} > 0 )); then

    echo "Verificando/compilando o executavel..."
    ./ns3 build cubic-experiment

    # Execucao sequencial: apenas uma simulacao por vez.
    for task in "${TASKS[@]}"; do

        IFS='|' read -r profile bandwidth delay mode run protocol access_delays run_dir <<< "$task"

        args="--transport_prot=$protocol
            --num_flows=$NUM_FLOWS
            --access_delays=$access_delays
            --bandwidth=$bandwidth
            --delay=${delay}ms
            --access_bandwidth=$ACCESS_BANDWIDTH
            --warmup=$WARMUP
            --duration=$DURATION
            --random_start_max=$RANDOM_START_MAX
            --queue_bdp=$QUEUE_BDP
            --run=$run
            --tracing=false
            --flow_monitor=true
            --results_dir=$run_dir"

        if [[ "$mode" == "adaptive" ]]; then
            args="$args --ns3::TcpCubicRtt::Alpha=$ALPHA_ADAPTIVE --ns3::TcpCubicRtt::Gamma=$GAMMA_ADAPTIVE"

        elif [[ "$mode" == "fixed" ]]; then
            args="$args --ns3::TcpCubicRtt::Alpha=0 --ns3::TcpCubicRtt::Gamma=0"
        fi

        echo ""
        echo "[INICIANDO] $profile | $bandwidth | ${delay}ms | $mode | run=$run"

        if ./ns3 run --no-build "cubic-experiment $args" > "$run_dir/execution.log" 2>&1 &&
           [[ -s "$run_dir/CubicExperiment.flowmonitor" ]] &&
           python3 -c 'import sys, xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' "$run_dir/CubicExperiment.flowmonitor" >/dev/null 2>&1; then

            touch "$run_dir/DONE"
            EXECUTED=$((EXECUTED + 1))

            echo "[OK] $profile/$bandwidth/${delay}ms/$mode/run_$run"

        else
            FAILED=$((FAILED + 1))

            echo "[FALHA] $profile/$bandwidth/${delay}ms/$mode/run_$run" >&2
            echo "Consulte: $run_dir/execution.log" >&2
        fi

        echo "Progresso: executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED total=$EXPECTED"
    done
fi

echo ""
echo "============================================"
echo "FIM DA CAMPANHA"
echo "Executadas: $EXECUTED"
echo "Puladas: $SKIPPED"
echo "Falhas: $FAILED"
echo "Planejadas: $EXPECTED"
echo "============================================"

(( FAILED == 0 ))
