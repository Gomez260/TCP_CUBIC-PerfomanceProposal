#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/TCP_CUBIC-PerfomanceProposal}"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"
RESULTS_DIR="$PROJECT_DIR/results/fixed_parameter_campaign"
REPETITIONS="${REPETITIONS:-5}"
NUM_FLOWS=4
ACCESS_BANDWIDTH="${ACCESS_BANDWIDTH:-1Gbps}"
WARMUP=20
DURATION=300
RANDOM_START_MAX=2
QUEUE_BDP=1
ALPHA_ADAPTIVE="${ALPHA_ADAPTIVE:-0.25}"
GAMMA_ADAPTIVE="${GAMMA_ADAPTIVE:-0.05}"

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

echo "CAMPANHA: CUBIC ORIGINAL x CUBIC-RTT ADAPTATIVO x FIXO"
echo "Adaptativo: Alpha=$ALPHA_ADAPTIVE Gamma=$GAMMA_ADAPTIVE"
echo "Fixo: Alpha=0 Gamma=0 => C=0.4 Beta=0.7 (defaults da implementação)"
echo "Perfis: low, heterogeneous, high | bandas: ${BANDWIDTHS[*]}"
echo "Atrasos do gargalo: ${DELAYS[*]} ms | repetições: $REPETITIONS"
echo "Warmup: ${WARMUP}s | medição: ${DURATION}s | fila: $QUEUE_BDP BDP"
echo "Total planejado: $EXPECTED"

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
                        continue
                    fi

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
                        --tracing=true
                        --flow_monitor=true
                        --results_dir=$run_dir"
                    if [[ "$mode" == "adaptive" ]]; then
                        args="$args --ns3::TcpCubicRtt::Alpha=$ALPHA_ADAPTIVE --ns3::TcpCubicRtt::Gamma=$GAMMA_ADAPTIVE"
                    elif [[ "$mode" == "fixed" ]]; then
                        args="$args --ns3::TcpCubicRtt::Alpha=0 --ns3::TcpCubicRtt::Gamma=0"
                    fi

                    echo "[EXECUTANDO] $profile | $bandwidth | ${delay}ms | $mode | run=$run"
                    if ./ns3 run "cubic-experiment $args" > "$run_dir/execution.log" 2>&1 && [[ -s "$flowmonitor" ]]; then
                        touch "$run_dir/DONE"
                        EXECUTED=$((EXECUTED + 1))
                        echo "[OK]"
                    else
                        FAILED=$((FAILED + 1))
                        echo "[FALHA] consulte $run_dir/execution.log"
                    fi
                    echo "executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED"
                done
            done
        done
    done
done

echo "FIM | executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED planejadas=$EXPECTED"
(( FAILED == 0 ))
