#!/bin/bash

NS3_DIR="$HOME/TCP_CUBIC-PerfomanceProposal/ns3/ns-3-dev-git"
RESULTS_DIR="$HOME/TCP_CUBIC-PerfomanceProposal/results"

cd "$NS3_DIR" || exit 1

NUM_REPETITIONS=5
NUM_FLOWS=4
BANDWIDTH="2Mbps"
ACCESS_BANDWIDTH="10Mbps"
ACCESS_DELAY="45ms"
DURATION=100

run_experiment() {

    local algorithm="$1"
    local delay="$2"
    local run="$3"

    local output_dir="$RESULTS_DIR/$algorithm/atraso_${delay}/run_${run}"

    mkdir -p "$output_dir"

    echo "======================================"
    echo "Algoritmo: $algorithm"
    echo "Atraso: $delay"
    echo "Repetição: $run"
    echo "======================================"

    ./ns3 run "cubic-experiment \
    --transport_prot=Tcp${algorithm} \
    --num_flows=$NUM_FLOWS \
    --bandwidth=$BANDWIDTH \
    --delay=${delay}ms \
    --access_bandwidth=$ACCESS_BANDWIDTH \
    --access_delay=$ACCESS_DELAY \
    --duration=$DURATION \
    --run=$run \
    --tracing=true \
    --flow_monitor=true \
    --results_dir=$output_dir"

    if [ $? -ne 0 ]; then
        echo "ERRO: $algorithm, atraso $delay ms, repetição $run"
        exit 1
    fi
}

for algorithm in Cubic Bbr
do
    for delay in 10 50 100
    do
        for run in $(seq 1 $NUM_REPETITIONS)
        do
            run_experiment "$algorithm" "$delay" "$run"
        done
    done
done

echo "======================================"
echo "30 SIMULAÇÕES CONCLUÍDAS!"
echo "======================================"