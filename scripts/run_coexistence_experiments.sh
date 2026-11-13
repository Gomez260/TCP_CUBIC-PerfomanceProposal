#!/usr/bin/env bash
set -euo pipefail

# Coexistencia: quatro classes de RTT, com um fluxo CUBIC e um CUBIC-RTT
# em cada classe. A ordem dos algoritmos corresponde a flow0 ... flow7.
PROJECT_DIR="${PROJECT_DIR:-$HOME/TCP_CUBIC-PerfomanceProposal}"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"
RESULTS_DIR="$PROJECT_DIR/results/coexistence_experiments"

REPETITIONS="${REPETITIONS:-5}"
DELAYS=(10 50 100)
NUM_FLOWS=8
BANDWIDTH="${BANDWIDTH:-10Mbps}"
ACCESS_BANDWIDTH="${ACCESS_BANDWIDTH:-1Gbps}"
ACCESS_DELAYS="10ms,10ms,30ms,30ms,60ms,60ms,90ms,90ms"
FLOW_ALGORITHMS="TcpCubic,TcpCubicRtt,TcpCubic,TcpCubicRtt,TcpCubic,TcpCubicRtt,TcpCubic,TcpCubicRtt"
WARMUP=20
DURATION=300
RANDOM_START_MAX=2
QUEUE_BDP=1
ALPHA="${ALPHA:-0.25}"
GAMMA="${GAMMA:-0.05}"

cd "$NS3_DIR" || {
    echo "ERRO: ns-3 não encontrado em $NS3_DIR" >&2
    exit 1
}
mkdir -p "$RESULTS_DIR"

EXPECTED=$((${#DELAYS[@]} * REPETITIONS))
EXECUTED=0
SKIPPED=0
FAILED=0

echo "CAMPANHA DE CONVIVÊNCIA CUBIC / CUBIC-RTT"
echo "Fluxos 0..7: CUBIC/CUBIC-RTT alternados em cada classe de RTT"
echo "Atrasos de acesso: $ACCESS_DELAYS"
echo "Gargalo: $BANDWIDTH | warmup: ${WARMUP}s | medição: ${DURATION}s"
echo "Alpha=$ALPHA Gamma=$GAMMA | BDP=$QUEUE_BDP"
echo "Planejadas: $EXPECTED"

for delay in "${DELAYS[@]}"; do
    for run in $(seq 1 "$REPETITIONS"); do
        run_dir="$RESULTS_DIR/8flows_heterogeneous/${delay}ms/run_$run"
        flowmonitor="$run_dir/CubicExperiment.flowmonitor"
        mkdir -p "$run_dir"

        if [[ -s "$flowmonitor" ]]; then
            echo "[PULANDO] ${delay}ms/run_$run (FlowMonitor já existe)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi

        echo "[EXECUTANDO] coexistência | gargalo=${delay}ms | run=$run"
        cmd="cubic-experiment \
            --transport_prot=TcpCubicRtt \
            --flow_algorithms=$FLOW_ALGORITHMS \
            --num_flows=$NUM_FLOWS \
            --access_delays=$ACCESS_DELAYS \
            --bandwidth=$BANDWIDTH \
            --delay=${delay}ms \
            --access_bandwidth=$ACCESS_BANDWIDTH \
            --warmup=$WARMUP \
            --duration=$DURATION \
            --random_start_max=$RANDOM_START_MAX \
            --queue_bdp=$QUEUE_BDP \
            --run=$run \
            --tracing=true \
            --flow_monitor=true \
            --results_dir=$run_dir \
            --ns3::TcpCubicRtt::Alpha=$ALPHA \
            --ns3::TcpCubicRtt::Gamma=$GAMMA"

        if ./ns3 run "$cmd" > "$run_dir/execution.log" 2>&1 && [[ -s "$flowmonitor" ]]; then
            EXECUTED=$((EXECUTED + 1))
            echo "[OK] ${delay}ms/run_$run"
        else
            FAILED=$((FAILED + 1))
            echo "[FALHA] ${delay}ms/run_$run - consulte $run_dir/execution.log"
        fi
        echo "executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED"
    done
done

echo "FIM | executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED planejadas=$EXPECTED"
(( FAILED == 0 ))
