#!/usr/bin/env bash
set -uo pipefail

PROJECT_DIR="${HOME}/TCP_CUBIC-PerfomanceProposal"
NS3_DIR="${PROJECT_DIR}/ns3/ns-3-dev-git"
RESULTS_DIR="${PROJECT_DIR}/results/robustness_experiments"
LOG_FILE="${PROJECT_DIR}/robustness_execution.log"

# Mantidos para preservar o desenho experimental original.
DURATION=100
REPETITIONS=5
DELAYS=(10 50 100)
SCENARIOS=(
    "bw1_f4 1Mbps 4 45ms"
    "bw2_f8 2Mbps 8 45ms"
    "access100 2Mbps 4 100ms"
)
CONFIGS=(
    "Cubic TcpCubic - -"
    "Bbr TcpBbr - -"
    "CubicRtt_A0.25_G0.05 TcpCubicRtt 0.25 0.05"
    "CubicRtt_A0.10_G0.00 TcpCubicRtt 0.10 0.00"
    "CubicRtt_A0.10_G0.025 TcpCubicRtt 0.10 0.025"
    "CubicRtt_A0.10_G0.05 TcpCubicRtt 0.10 0.05"
    "CubicRtt_A0.10_G0.10 TcpCubicRtt 0.10 0.10"
    "CubicRtt_A0.25_G0.00 TcpCubicRtt 0.25 0.00"
    "CubicRtt_A0.25_G0.025 TcpCubicRtt 0.25 0.025"
    "CubicRtt_A0.50_G0.00 TcpCubicRtt 0.50 0.00"
    "CubicRtt_A0.50_G0.025 TcpCubicRtt 0.50 0.025"
    "CubicRtt_A0.75_G0.00 TcpCubicRtt 0.75 0.00"
    "CubicRtt_A0.75_G0.025 TcpCubicRtt 0.75 0.025"
    "CubicRtt_A0.75_G0.05 TcpCubicRtt 0.75 0.05"
    "CubicRtt_A0.75_G0.10 TcpCubicRtt 0.75 0.10"
)

if [[ ! -d "$NS3_DIR" ]]; then
    echo "ERRO: ns-3 nao encontrado: $NS3_DIR" >&2
    exit 1
fi

mkdir -p "$RESULTS_DIR"
cd "$NS3_DIR" || exit 1

EXPECTED=$((
    ${#SCENARIOS[@]} * ${#CONFIGS[@]} * ${#DELAYS[@]} * REPETITIONS
))
EXECUTED=0
SKIPPED=0
FAILED=0

{
    echo "BATERIA ROBUSTEZ | $(date) | esperadas=$EXPECTED"
    echo "Build esperado: optimized | duracao=$DURATION s | repeticoes=$REPETITIONS"
    echo "Tracing mantido: o analisador extrai cwnd, RTT, inflight e ssth dos traces."

    for scenario_config in "${SCENARIOS[@]}"; do
        read -r scenario bandwidth num_flows access_delay <<< "$scenario_config"

        for config in "${CONFIGS[@]}"; do
            read -r label protocol alpha gamma <<< "$config"

            for delay in "${DELAYS[@]}"; do
                for run in $(seq 1 "$REPETITIONS"); do
                    run_dir="$RESULTS_DIR/$scenario/$label/${delay}ms/run_$run"
                    xml="$run_dir/CubicExperiment.flowmonitor"
                    done_file="$run_dir/DONE"

                    mkdir -p "$run_dir"

                    # DONE e criado com touch (arquivo vazio): testar -f, nao -s.
                    if [[ -f "$done_file" && -s "$xml" ]]; then
                        echo "[PULANDO] $scenario/$label/${delay}ms/run_$run"
                        SKIPPED=$((SKIPPED + 1))
                        continue
                    fi

                    rm -f "$done_file"

                    cmd=(
                        "cubic-experiment"
                        "--transport_prot=$protocol"
                        "--num_flows=$num_flows"
                        "--bandwidth=$bandwidth"
                        "--delay=${delay}ms"
                        "--access_bandwidth=10Mbps"
                        "--access_delay=$access_delay"
                        "--duration=$DURATION"
                        "--tracing=true"
                        "--flow_monitor=true"
                        "--results_dir=$run_dir"
                        "--run=$run"
                    )

                    if [[ "$protocol" == "TcpCubicRtt" ]]; then
                        cmd+=(
                            "--ns3::TcpCubicRtt::Alpha=$alpha"
                            "--ns3::TcpCubicRtt::Gamma=$gamma"
                        )
                    fi

                    echo "[EXECUTANDO] $scenario/$label/${delay}ms/run_$run"

                    if ./ns3 run "${cmd[*]}" > "$run_dir/execution.log" 2>&1 \
                        && [[ -s "$xml" ]]; then
                        touch "$done_file"
                        EXECUTED=$((EXECUTED + 1))
                        echo "[OK]"
                    else
                        FAILED=$((FAILED + 1))
                        echo "[FALHA] veja $run_dir/execution.log"
                    fi

                    echo "executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED"
                done
            done
        done
    done

    echo "FIM | executadas=$EXECUTED puladas=$SKIPPED falhas=$FAILED esperadas=$EXPECTED"
} 2>&1 | tee -a "$LOG_FILE"
