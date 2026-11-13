#!/usr/bin/env bash
set -euo pipefail

# Matriz de cenários para avaliar robustez sob diferentes RTTs e capacidades.
# Mantém 4 fluxos CUBIC-RTT e varia somente perfil de RTT, banda e atraso do gargalo.
PROJECT_DIR="${PROJECT_DIR:-$HOME/TCP_CUBIC-PerfomanceProposal}"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"
RESULTS_DIR="$PROJECT_DIR/results/scenario_variation"

REPETITIONS="${REPETITIONS:-5}"
NUM_FLOWS=4
ACCESS_BANDWIDTH="${ACCESS_BANDWIDTH:-1Gbps}"
WARMUP=20
DURATION=300
RANDOM_START_MAX=2
QUEUE_BDP=1
ALPHA="${ALPHA:-0.25}"
GAMMA="${GAMMA:-0.05}"

# Cada perfil tem quatro atrasos individuais de acesso (um por fluxo).
declare -A ACCESS_PROFILES=(
    [low]="5ms,10ms,15ms,20ms"
    [heterogeneous]="10ms,30ms,60ms,90ms"
    [high]="30ms,60ms,90ms,120ms"
)
BANDWIDTHS=(10Mbps 50Mbps 100Mbps)
DELAYS=(10 50 100)

cd "$NS3_DIR" || {
    echo "ERRO: ns-3 não encontrado em $NS3_DIR" >&2
    exit 1
}
mkdir -p "$RESULTS_DIR"

EXPECTED=$((${#ACCESS_PROFILES[@]} * ${#BANDWIDTHS[@]} * ${#DELAYS[@]} * REPETITIONS))
EXECUTED=0
SKIPPED=0
FAILED=0

echo "CAMPANHA DE VARIAÇÃO DE CENÁRIOS CUBIC-RTT"
echo "Perfis: low, heterogeneous, high"
echo "Bandas: ${BANDWIDTHS[*]} | atrasos de gargalo: ${DELAYS[*]} ms"
echo "Repetições: $REPETITIONS | duração medida: ${DURATION}s | fila: $QUEUE_BDP BDP"
echo "Planejadas: $EXPECTED"

for profile in low heterogeneous high; do
    access_delays="${ACCESS_PROFILES[$profile]}"
    for bandwidth in "${BANDWIDTHS[@]}"; do
        for delay in "${DELAYS[@]}"; do
            for run in $(seq 1 "$REPETITIONS"); do
                run_dir="$RESULTS_DIR/$profile/${bandwidth}/${delay}ms/run_$run"
                flowmonitor="$run_dir/CubicExperiment.flowmonitor"
                mkdir -p "$run_dir"

                if [[ -s "$flowmonitor" ]]; then
                    echo "[PULANDO] $profile/$bandwidth/${delay}ms/run_$run"
                    SKIPPED=$((SKIPPED + 1))
                    continue
                fi

                echo "[EXECUTANDO] perfil=$profile banda=$bandwidth atraso=${delay}ms run=$run"
                cmd="cubic-experiment \
                    --transport_prot=TcpCubicRtt \
                    --num_flows=$NUM_FLOWS \
                    --access_delays=$access_delays \
                    --bandwidth=$bandwidth \
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
                    echo "[OK] $profile/$bandwidth/${delay}ms/run_$run"
                else
                    FAILED=$((FAILED + 1))
                    echo "[FALHA] $profile/$bandwidth/${delay}ms/run_$run - consulte $run_dir/execution.log"
                fi
                echo "executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED"
            done
        done
    done
done

echo "FIM | executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED planejadas=$EXPECTED"
(( FAILED == 0 ))
