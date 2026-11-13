#!/usr/bin/env python3
"""Consolida a campanha e gera gráficos em results/fixed_parameter_campaign/graphs."""

import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import consolidate_results as base

PROJECT_DIR = base.PROJECT_DIR
INPUT_DIR = os.path.join(PROJECT_DIR, "results", "fixed_parameter_campaign")
OUTPUT_DIR = os.path.join(INPUT_DIR, "analysis")
GRAPH_DIR = os.path.join(INPUT_DIR, "graphs")
PROFILES = ("low", "heterogeneous", "high")
BANDWIDTHS = ("10Mbps", "50Mbps", "100Mbps")
DELAYS = (10, 50, 100)
MODES = ("cubic", "adaptive", "fixed")
LABELS = {
    "cubic": "CUBIC original",
    "adaptive": "CUBIC-RTT adaptativo",
    "fixed": "CUBIC-RTT fixo (C=0.4, Beta=0.7)",
}
RUNS = range(1, 6)
METRICS = ("throughput_mbps", "loss_rate_pct", "avg_delay_ms", "avg_jitter_ms", "jain_fairness")
Y_LABELS = {
    "throughput_mbps": "Vazão agregada (Mbps)",
    "loss_rate_pct": "Taxa de perdas (%)",
    "avg_delay_ms": "Atraso médio fim a fim (ms)",
    "avg_jitter_ms": "Jitter médio (ms)",
    "jain_fairness": "Índice de justiça de Jain",
}


def write_csv(path, rows):
    if rows:
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def jain_fairness(flows):
    if not flows:
        return None
    first = min(row["first_rx_ns"] for row in flows)
    last = max(row["last_rx_ns"] for row in flows)
    duration = (last - first) / 1e9
    if duration <= 0:
        return None
    rates = [row["rx_bytes"] * 8 / duration for row in flows]
    total = sum(rates)
    squares = sum(rate * rate for rate in rates)
    return total * total / (len(rates) * squares) if squares else None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(GRAPH_DIR, exist_ok=True)
    simulations = []
    warnings = []
    expected = len(PROFILES) * len(BANDWIDTHS) * len(DELAYS) * len(MODES) * len(RUNS)

    for profile in PROFILES:
        for bandwidth in BANDWIDTHS:
            for delay in DELAYS:
                for mode in MODES:
                    for run in RUNS:
                        folder = os.path.join(INPUT_DIR, profile, bandwidth, f"{delay}ms", mode, f"run_{run}")
                        xml = os.path.join(folder, "CubicExperiment.flowmonitor")
                        if not os.path.isfile(xml) or os.path.getsize(xml) == 0:
                            warnings.append(f"FlowMonitor ausente/vazio: {xml}")
                            continue
                        try:
                            flows = base.analyzer.parse_flowmonitor(xml)
                            summary = base.calculate_summary(flows)
                        except Exception as error:
                            warnings.append(f"Falha ao analisar {xml}: {error}")
                            continue
                        if len(flows) != 4:
                            warnings.append(f"{profile}/{bandwidth}/{delay}ms/{mode}/run_{run}: {len(flows)} fluxos, esperado 4")
                        simulations.append({
                            "profile": profile, "bandwidth": bandwidth,
                            "bottleneck_delay_ms": delay, "mode": mode,
                            "algorithm": LABELS[mode], "repetition": run,
                            **summary, "jain_fairness": jain_fairness(flows),
                        })

    write_csv(os.path.join(OUTPUT_DIR, "resumo_simulacoes.csv"), simulations)
    grouped = defaultdict(list)
    for row in simulations:
        for metric in METRICS:
            grouped[(row["profile"], row["bandwidth"], row["bottleneck_delay_ms"], row["mode"], metric)].append(row.get(metric))

    aggregate = []
    for (profile, bandwidth, delay, mode, metric), values in sorted(grouped.items()):
        values = [float(value) for value in values if value is not None]
        aggregate.append({
            "profile": profile, "bandwidth": bandwidth, "bottleneck_delay_ms": delay,
            "mode": mode, "metric": metric, "n": len(values),
            "mean": statistics.mean(values) if values else None,
            "std": statistics.stdev(values) if len(values) > 1 else None,
        })
    write_csv(os.path.join(OUTPUT_DIR, "resumo_estatistico.csv"), aggregate)

    for profile in PROFILES:
        for bandwidth in BANDWIDTHS:
            for metric in METRICS:
                fig, ax = plt.subplots(figsize=(8, 5))
                has_data = False
                for mode in MODES:
                    rows = [row for row in aggregate if row["profile"] == profile
                            and row["bandwidth"] == bandwidth and row["mode"] == mode
                            and row["metric"] == metric and row["mean"] is not None]
                    rows.sort(key=lambda row: row["bottleneck_delay_ms"])
                    if rows:
                        ax.errorbar(
                            [row["bottleneck_delay_ms"] for row in rows],
                            [row["mean"] for row in rows],
                            yerr=[row["std"] or 0 for row in rows],
                            marker="o", capsize=4, label=LABELS[mode],
                        )
                        has_data = True
                if not has_data:
                    plt.close(fig)
                    continue
                ax.set_xlabel("Atraso do gargalo (ms)")
                ax.set_ylabel(Y_LABELS[metric])
                ax.set_title(f"{Y_LABELS[metric]} | perfil {profile} | gargalo {bandwidth}")
                ax.grid(True, alpha=0.3)
                ax.legend()
                fig.tight_layout()
                fig.savefig(os.path.join(GRAPH_DIR, f"{profile}_{bandwidth}_{metric}.png"), dpi=160)
                plt.close(fig)

    report_path = os.path.join(OUTPUT_DIR, "relatorio_validacao.txt")
    with open(report_path, "w", encoding="utf-8") as report:
        report.write("RELATORIO - CAMPANHA DE PARAMETROS FIXOS\n")
        report.write("=" * 58 + "\n")
        report.write("Fixo: TcpCubicRtt com Alpha=0 e Gamma=0; defaults C=0.4 e Beta=0.7.\n")
        report.write("Adaptativo: TcpCubicRtt com Alpha=0.25 e Gamma=0.05 (valores configuráveis).\n")
        report.write("Referência: TcpCubic original.\n")
        report.write(f"Simulações planejadas: {expected}\n")
        report.write(f"Simulações analisadas: {len(simulations)}\n")
        report.write(f"Ocorrências: {len(warnings)}\n")
        report.write(f"Gráficos: {GRAPH_DIR}\n\n")
        for warning in warnings:
            report.write("- " + warning + "\n")
        if not warnings:
            report.write("Nenhuma ausência estrutural detectada.\n")

    print(f"Simulações analisadas: {len(simulations)}/{expected}")
    print(f"Ocorrências: {len(warnings)}")
    print(f"CSV/relatório: {OUTPUT_DIR}")
    print(f"Gráficos: {GRAPH_DIR}")


if __name__ == "__main__":
    main()
