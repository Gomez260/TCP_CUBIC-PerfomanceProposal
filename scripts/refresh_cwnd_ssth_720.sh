
#!/usr/bin/env bash
set -uo pipefail

# ==========================================================
# REGERAÇÃO DOS RASTROS CWND E SSTHRESH
# 45 simulações iniciais + 675 de robustez = 720
# ==========================================================

PROJECT_DIR="${HOME}/TCP_CUBIC-PerfomanceProposal"
NS3_DIR="$PROJECT_DIR/ns3/ns-3-dev-git"
RESULTS_DIR="$PROJECT_DIR/results"

STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$RESULTS_DIR/trace_refresh_backup_$STAMP"
LOG_DIR="$PROJECT_DIR/logs/trace_refresh_$STAMP"
TMP_ROOT="${TMPDIR:-/tmp}"

DURATION=100
REPETITIONS=5
DELAYS=(10 50 100)

INITIAL_ALGORITHMS=(
    "Cubic TcpCubic"
    "Bbr TcpBbr"
    "CubicRtt TcpCubicRtt"
)

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

EXPECTED=720
EXECUTED=0
FAILED=0

mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# ----------------------------------------------------------
# Verificações iniciais
# ----------------------------------------------------------

if [[ ! -d "$NS3_DIR" ]]; then
    echo "[ERRO] Diretório ns-3 não encontrado: $NS3_DIR"
    exit 1
fi

cd "$NS3_DIR" || exit 1

echo "=========================================================="
echo "REGERAÇÃO DOS RASTROS CWND / SSTHRESH"
echo "Início: $(date)"
echo "Total esperado: $EXPECTED simulações"
echo "Backup: $BACKUP_DIR"
echo "Logs: $LOG_DIR"
echo "=========================================================="

echo "[1/3] Verificando as pastas originais..."

MISSING=0

for algorithm in Cubic Bbr CubicRtt; do
    for delay in "${DELAYS[@]}"; do
        for run in $(seq 1 "$REPETITIONS"); do
            dir="$RESULTS_DIR/$algorithm/atraso_$delay/run_$run"

            if [[ ! -d "$dir" ]]; then
                echo "[AUSENTE] $dir"
                MISSING=$((MISSING + 1))
            fi
        done
    done
done

for scenario_info in "${SCENARIOS[@]}"; do
    read -r scenario bandwidth flows access_delay <<< "$scenario_info"

    for config in "${CONFIGS[@]}"; do
        read -r label protocol alpha gamma <<< "$config"

        for delay in "${DELAYS[@]}"; do
            for run in $(seq 1 "$REPETITIONS"); do
                dir="$RESULTS_DIR/robustness_experiments/$scenario/$label/${delay}ms/run_$run"

                if [[ ! -d "$dir" ]]; then
                    echo "[AUSENTE] $dir"
                    MISSING=$((MISSING + 1))
                fi
            done
        done
    done
done

if [[ "$MISSING" -gt 0 ]]; then
    echo "[ERRO] Foram encontradas $MISSING pastas ausentes."
    echo "Nenhuma simulação foi iniciada."
    exit 1
fi

echo "[OK] As 720 pastas originais foram encontradas."

# ----------------------------------------------------------
# Compilação
# ----------------------------------------------------------

echo
echo "[2/3] Compilando cubic-experiment..."

if ! ./ns3 build cubic-experiment > "$LOG_DIR/build.log" 2>&1; then
    echo "[ERRO] Falha na compilação. Consulte:"
    echo "$LOG_DIR/build.log"
    exit 1
fi

echo "[OK] Compilação concluída."

# ----------------------------------------------------------
# Execução de uma simulação temporária
# ----------------------------------------------------------

run_one() {
    local category="$1"
    local relative_dir="$2"
    local protocol="$3"
    local flows="$4"
    local bandwidth="$5"
    local access_delay="$6"
    local delay="$7"
    local run="$8"
    local alpha="$9"
    local gamma="${10}"

    local target_dir="$RESULTS_DIR/$relative_dir"
    local safe_name="${relative_dir//\//__}"
    local log_file="$LOG_DIR/${safe_name}.log"

    local temp_dir
    temp_dir=$(mktemp -d "$TMP_ROOT/tcp-cubic-refresh.XXXXXX") || {
        echo "[FALHA] Não foi possível criar diretório temporário."
        FAILED=$((FAILED + 1))
        return
    }

    local command="cubic-experiment"
    command+=" --transport_prot=$protocol"
    command+=" --num_flows=$flows"
    command+=" --bandwidth=$bandwidth"
    command+=" --delay=${delay}ms"
    command+=" --access_bandwidth=10Mbps"
    command+=" --access_delay=$access_delay"
    command+=" --duration=$DURATION"
    command+=" --tracing=true"
    command+=" --flow_monitor=true"
    command+=" --results_dir=$temp_dir"
    command+=" --run=$run"

    # Nas 45 simulações iniciais, os valores padrão
    # do TCP CUBIC-RTT são preservados.
    if [[ "$protocol" == "TcpCubicRtt" && "$alpha" != "-" ]]; then
        command+=" --ns3::TcpCubicRtt::Alpha=$alpha"
        command+=" --ns3::TcpCubicRtt::Gamma=$gamma"
    fi

    echo
    echo "[EXECUTANDO] $category/$relative_dir"

    if ! ./ns3 run "$command" > "$log_file" 2>&1; then
        echo "[FALHA] Erro na simulação."
        echo "Log: $log_file"
        echo "Temporário preservado: $temp_dir"
        echo "$temp_dir" >> "$LOG_DIR/failed_temp_dirs.txt"
        FAILED=$((FAILED + 1))
        return
    fi

    # Verifica o FlowMonitor gerado.
    if [[ ! -s "$temp_dir/CubicExperiment.flowmonitor" ]]; then
        echo "[FALHA] FlowMonitor ausente ou vazio."
        echo "Temporário preservado: $temp_dir"
        echo "$temp_dir" >> "$LOG_DIR/failed_temp_dirs.txt"
        FAILED=$((FAILED + 1))
        return
    fi

    # Primeiro valida todos os rastros esperados.
    local i
    local valid=true

    for ((i=0; i<flows; i++)); do
        local cwnd="$temp_dir/CubicExperiment-flow${i}-cwnd.data"
        local ssth="$temp_dir/CubicExperiment-flow${i}-ssth.data"

        if [[ ! -s "$cwnd" || ! -s "$ssth" ]]; then
            echo "[FALHA] Rastros ausentes ou vazios para fluxo $i."
            valid=false
        fi
    done

    if [[ "$valid" != true ]]; then
        echo "Temporário preservado: $temp_dir"
        echo "$temp_dir" >> "$LOG_DIR/failed_temp_dirs.txt"
        FAILED=$((FAILED + 1))
        return
    fi

    # Faz backup dos rastros antigos antes de substituí-los.
    local backup_target="$BACKUP_DIR/$relative_dir"
    mkdir -p "$backup_target"

    for ((i=0; i<flows; i++)); do
        for metric in cwnd ssth; do
            local filename="CubicExperiment-flow${i}-${metric}.data"

            if [[ -f "$target_dir/$filename" ]]; then
                if ! cp -p "$target_dir/$filename" "$backup_target/$filename"; then
                    echo "[FALHA] Não foi possível fazer backup de $filename."
                    echo "Temporário preservado: $temp_dir"
                    FAILED=$((FAILED + 1))
                    return
                fi
            fi
        done
    done

    # Copia somente CWND e SSThresh.
    for ((i=0; i<flows; i++)); do
        for metric in cwnd ssth; do
            local filename="CubicExperiment-flow${i}-${metric}.data"

            if ! cp -p "$temp_dir/$filename" "$target_dir/$filename"; then
                echo "[FALHA] Erro copiando $filename."
                echo "Temporário preservado: $temp_dir"
                FAILED=$((FAILED + 1))
                return
            fi
        done
    done

    # Confere se os arquivos copiados são idênticos.
    for ((i=0; i<flows; i++)); do
        for metric in cwnd ssth; do
            local filename="CubicExperiment-flow${i}-${metric}.data"

            if ! cmp -s "$temp_dir/$filename" "$target_dir/$filename"; then
                echo "[FALHA] Divergência após cópia: $filename."
                FAILED=$((FAILED + 1))
                return
            fi
        done
    done

    rm -rf -- "$temp_dir"

    EXECUTED=$((EXECUTED + 1))

    echo "[OK] Rastros atualizados."
    echo "Progresso: $EXECUTED/$EXPECTED | Falhas: $FAILED"
}

# ----------------------------------------------------------
# Campanha inicial: 45 simulações
# ----------------------------------------------------------

echo
echo "=========================================================="
echo "CAMPANHA INICIAL: 45 SIMULAÇÕES"
echo "=========================================================="

for algorithm_info in "${INITIAL_ALGORITHMS[@]}"; do
    read -r algorithm protocol <<< "$algorithm_info"

    for delay in "${DELAYS[@]}"; do
        for run in $(seq 1 "$REPETITIONS"); do
            relative_dir="$algorithm/atraso_$delay/run_$run"

            run_one \
                "INICIAL" \
                "$relative_dir" \
                "$protocol" \
                4 \
                "2Mbps" \
                "45ms" \
                "$delay" \
                "$run" \
                "-" \
                "-"
        done
    done
done

# ----------------------------------------------------------
# Campanha de robustez: 675 simulações
# ----------------------------------------------------------

echo
echo "=========================================================="
echo "CAMPANHA DE ROBUSTEZ: 675 SIMULAÇÕES"
echo "=========================================================="

for scenario_info in "${SCENARIOS[@]}"; do
    read -r scenario bandwidth flows access_delay <<< "$scenario_info"

    for config in "${CONFIGS[@]}"; do
        read -r label protocol alpha gamma <<< "$config"

        for delay in "${DELAYS[@]}"; do
            for run in $(seq 1 "$REPETITIONS"); do
                relative_dir="robustness_experiments/$scenario/$label/${delay}ms/run_$run"

                run_one \
                    "ROBUSTEZ" \
                    "$relative_dir" \
                    "$protocol" \
                    "$flows" \
                    "$bandwidth" \
                    "$access_delay" \
                    "$delay" \
                    "$run" \
                    "$alpha" \
                    "$gamma"
            done
        done
    done
done

# ----------------------------------------------------------
# Relatório final
# ----------------------------------------------------------

echo
echo "=========================================================="
echo "EXECUÇÃO FINALIZADA"
echo "=========================================================="
echo "Esperadas:  $EXPECTED"
echo "Concluídas: $EXECUTED"
echo "Falhas:     $FAILED"
echo "Backup:     $BACKUP_DIR"
echo "Logs:       $LOG_DIR"
echo "Fim:        $(date)"

if [[ "$EXECUTED" -eq "$EXPECTED" && "$FAILED" -eq 0 ]]; then
    echo "[SUCESSO] Os 720 conjuntos de rastros foram atualizados."
    exit 0
else
    echo "[ATENÇÃO] Execução incompleta. Consulte os logs e as pastas temporárias preservadas."
    exit 1
fi
