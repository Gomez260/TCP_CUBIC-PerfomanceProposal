#!/bin/bash

NS3_DIR="$HOME/TCP_CUBIC-PerfomanceProposal/ns3/ns-3-dev-git"
RESULTS_DIR="$HOME/TCP_CUBIC-PerfomanceProposal/results/cubic"

cd "$NS3_DIR" || exit 1

echo "======================================"
echo "      EXPERIMENTOS TCP CUBIC"
echo "======================================"

echo ""
echo ">>> Cenário 01"
echo ""

./ns3 run "cubic-experiment \
--transport_prot=TcpCubic \
--num_flows=4 \
--bandwidth=2Mbps \
--delay=10ms \
--access_bandwidth=10Mbps \
--access_delay=45ms \
--duration=100 \
--tracing=true \
--flow_monitor=true \
--results_dir=$RESULTS_DIR/cenario01"

if [ $? -ne 0 ]; then
    echo "ERRO no Cenário 01"
    exit 1
fi

echo ""
echo "======================================"
echo "Cenário 01 concluído!"
echo "======================================"
