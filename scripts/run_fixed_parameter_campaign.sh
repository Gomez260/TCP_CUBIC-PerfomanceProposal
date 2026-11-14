#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/TCP_CUBIC-PerfomanceProposal}"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"
RESULTS_DIR="$PROJECT_DIR/results/fixed_parameter_campaign"
REPETITIONS="${REPETITIONS:-5}"
MAX_JOBS="${MAX_JOBS:-2}"
NUM_FLOWS=4
ACCESS_BANDWIDTH="${ACCESS_BANDWIDTH:-1Gbps}"
WARMUP=20
DURATION=300
RANDOM_START_MAX=2
QUEUE_BDP=1
ALPHA_ADAPTIVE="${ALPHA_ADAPTIVE:-0.25}"
GAMMA_ADAPTIVE="${GAMMA_ADAPTIVE:-0.05}"

if ! [[ "$MAX_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERRO: MAX_JOBS deve ser um inteiro positivo (atual: $MAX_JOBS)" >&2
    exit 1
fi

declare -A ACCESS_PROFILES=(
    [low]="5ms,10ms,15ms,20ms"
    [heterogeneous]="10ms,30ms,60ms,90ms"
    [high]="30ms,60ms,90ms,120ms"
)
BANDWIDTHS=(10Mbps 50Mbps 100Mbps)
DELAYS=(10 50 100)
declare -A PROTOCOLS=([cubic]="TcpCubic" [adaptive]="TcpCubicRtt" [fixed]="TcpCubicRtt")

cd "$NS3_DIR" || { echo "ERRO: ns-3 não encontrado em $NS3_DIR" >&2; exit 1; }
mkdir -p "$RESULTS_DIR"

EXPECTED=$((3 * 3 * 3 * 3 * REPETITIONS))
EXECUTED=0
SKIPPED=0
FAILED=0
TASKS=()

echo "CAMPANHA: CUBIC ORIGINAL x CUBIC-RTT ADAPTATIVO x FIXO"
echo "Adaptativo: Alpha=$ALPHA_ADAPTIVE Gamma=$GAMMA_ADAPTIVE"
echo "Fixo: Alpha=0 Gamma=0 => C=0.4 Beta=0.7 (defaults da implementação)"
echo "Perfis: low, heterogeneous, high | bandas: ${BANDWIDTHS[*]}"
echo "Atrasos do gargalo: ${DELAYS[*]} ms | repetições: $REPETITIONS"
echo "Warmup: ${WARMUP}s | medição: ${DURATION}s | fila: $QUEUE_BDP BDP"
echo "Concorrência: $MAX_JOBS simulações simultâneas"
echo "Total planejado: $EXPECTED"

# Monta a lista antes de iniciar os processos; cada simulação tem diretório exclusivo.
for profile in low heterogeneous high; do
    access_delays="${ACCESS_PROFILES[$profile]}"
    for bandwidth in "${BANDWIDTHS[@]}"; do
        for delay in "${DELAYS[@]}"; do
            for mode in cubic adaptive fixed; do
                protocol="${PROTOCOLS[$mode]}"
                for run in $(seq 1 "$REPETITIONS"); do
                    run_dir="$RESULTS_DIR/$profile/$bandwidth/${delay}ms/$mode/run_$run"
                    flowmonitor="$run_dir/CubicExperiment.flowmonitor"
                    mkdir -p "$run_dir"
                    if [[ -s "$flowmonitor" ]]; then
                        echo "[PULANDO] $profile/$bandwidth/${delay}ms/$mode/run_$run"
                        SKIPPED=$((SKIPPED + 1))
                    else
                        TASKS+=("$profile|$bandwidth|$delay|$mode|$run|$protocol|$access_delays|$run_dir")
                    fi
                done
            done
        done
    done
done

echo "Pendentes: ${#TASKS[@]} | já concluídas: $SKIPPED"

if (( ${#TASKS[@]} > 0 )); then
    echo "Verificando/compilando o executável uma única vez antes do paralelismo..."
    ./ns3 build cubic-experiment

    run_one() {
        local task="$1"
        local profile bandwidth delay mode run protocol access_delays run_dir
        IFS='|' read -r profile bandwidth delay mode run protocol access_delays run_dir <<< "$task"

        local args="--transport_prot=$protocol
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

        echo "[INICIANDO] $profile | $bandwidth | ${delay}ms | $mode | run=$run"
        if ./ns3 run --no-build "cubic-experiment $args" > "$run_dir/execution.log" 2>&1 \
            && [[ -s "$run_dir/CubicExperiment.flowmonitor" ]]; then
            touch "$run_dir/DONE"
            echo "[OK] $profile/$bandwidth/${delay}ms/$mode/run_$run"
            return 0
        fi

        echo "[FALHA] $profile/$bandwidth/${delay}ms/$mode/run_$run - consulte $run_dir/execution.log" >&2
        return 1
    }

    # Executa em lotes limitados. O wrapper do ns-3 não recompila dentro dos workers.
    for ((offset=0; offset<${#TASKS[@]}; offset+=MAX_JOBS)); do
        pids=()
        batch_tasks=()
        limit=$((offset + MAX_JOBS))
        (( limit > ${#TASKS[@]} )) && limit=${#TASKS[@]}

        for ((i=offset; i<limit; i++)); do
            run_one "${TASKS[$i]}" &
            pids+=("$!")
            batch_tasks+=("${TASKS[$i]}")
        done

        for i in "${!pids[@]}"; do
            if wait "${pids[$i]}"; then
                EXECUTED=$((EXECUTED + 1))
            else
                FAILED=$((FAILED + 1))
            fi
        done
        echo "Progresso: executadas nesta retomada=$EXECUTED puladas=$SKIPPED falhas=$FAILED planejadas=$EXPECTED"
    done
fi

echo "FIM | executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED planejadas=$EXPECTED"
(( FAILED == 0 ))
