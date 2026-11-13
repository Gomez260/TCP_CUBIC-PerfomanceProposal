#!/usr/bin/env python3
"""Consolida a campanha fatorial balanceada de Alpha/Gamma do CUBIC-RTT."""

import csv
import math
import os
import statistics
from collections import defaultdict

import consolidate_results as base

PROJECT_DIR = base.PROJECT_DIR
INPUT_DIR = os.path.join(PROJECT_DIR, "results", "parameter_experiments")
OUTPUT_DIR = os.path.join(INPUT_DIR, "consolidated")

ALPHAS = ("0.10", "0.25", "0.50")
GAMMAS = ("0.00", "0.05", "0.10")
EXPERIMENTS = tuple(
    f"A{alpha}_G{gamma}"
    for alpha in ALPHAS
    for gamma in GAMMAS
)
DELAYS = (10, 50, 100)
RUNS = range(1, 6)

# Valores críticos da distribuição t de Student para IC bilateral de 95%.
T_CRITICAL_95 = {
    2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571,
    7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 11: 2.228,
    12: 2.201, 13: 2.179, 14: 2.160, 15: 2.145, 16: 2.131,
    17: 2.120, 18: 2.110, 19: 2.101, 20: 2.093, 21: 2.086,
    22: 2.080, 23: 2.074, 24: 2.069, 25: 2.064, 26: 2.060,
    27: 2.056, 28: 2.052, 29: 2.048, 30: 2.045,
}


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def find_run_dir(experiment, delay, run):
    candidates = (
        os.path.join(INPUT_DIR, experiment, f"{delay}ms", f"run_{run}"),
        os.path.join(INPUT_DIR, experiment, f"{delay}ms", f"run{run}"),
        os.path.join(INPUT_DIR, experiment, f"atraso_{delay}", f"run_{run}"),
        os.path.join(INPUT_DIR, experiment, f"atraso_{delay}", f"run{run}"),
    )
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


def calculate_jain(results):
    if not results:
        return None
    first_rx = min(row["first_rx_ns"] for row in results)
    last_rx = max(row["last_rx_ns"] for row in results)
    duration = (last_rx - first_rx) / 1e9
    if duration <= 0:
        return None
    rates = [row["rx_bytes"] * 8 / duration for row in results]
    total = sum(rates)
    squares = sum(rate * rate for rate in rates)
    return total * total / (len(rates) * squares) if squares else None


def confidence_summary(values):
    values = [float(value) for value in values if value is not None]
    n = len(values)
    if not n:
        return {"n": 0, "mean": None, "std": None, "ci95_low": None, "ci95_high": None}
    mean = statistics.mean(values)
    if n == 1:
        return {"n": 1, "mean": mean, "std": None, "ci95_low": None, "ci95_high": None}
    std = statistics.stdev(values)
    critical = T_CRITICAL_95.get(n, 1.96)
    margin = critical * std / math.sqrt(n)
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    simulation_rows = []
    flow_rows = []
    warnings = []
    expected = len(EXPERIMENTS) * len(DELAYS) * len(RUNS)

    for experiment in EXPERIMENTS:
        alpha, gamma = experiment.split("_")
        alpha = alpha[1:]
        gamma = gamma[1:]
        for delay in DELAYS:
            for run in RUNS:
                run_dir = find_run_dir(experiment, delay, run)
                xml = os.path.join(run_dir, "CubicExperiment.flowmonitor")
                if not os.path.isfile(xml) or os.path.getsize(xml) == 0:
                    warnings.append(f"FlowMonitor ausente/vazio: {xml}")
                    continue
                try:
                    results = base.analyzer.parse_flowmonitor(xml)
                except Exception as error:
                    warnings.append(f"Erro lendo {xml}: {error}")
                    continue

                if len(results) != 4:
                    warnings.append(
                        f"{experiment}, {delay}ms, run {run}: "
                        f"{len(results)} fluxos; esperado 4"
                    )

                summary = base.calculate_summary(results)
                jain = calculate_jain(results)
                simulation_rows.append({
                    "experiment": experiment,
                    "alpha": alpha,
                    "gamma": gamma,
                    "baseline": alpha == "0.25" and gamma == "0.05",
                    "delay_ms": delay,
                    "repetition": run,
                    **summary,
                    "jain_fairness": jain,
                })

                for result in results:
                    flow_index = base.SOURCE_TO_TCP_FLOW.get(result["source"])
                    if flow_index is None:
                        warnings.append(
                            f"Origem sem índice TCP: {result['source']} em {xml}"
                        )
                        continue
                    flow_rows.append({
                        "experiment": experiment,
                        "alpha": alpha,
                        "gamma": gamma,
                        "delay_ms": delay,
                        "repetition": run,
                        "flowmonitor_id": result["flow"],
                        "tcp_flow_index": flow_index,
                        "source": result["source"],
                        "destination": result["destination"],
                        "tx_bytes": result["tx_bytes"],
                        "rx_bytes": result["rx_bytes"],
                        "tx_packets": result["tx_packets"],
                        "rx_packets": result["rx_packets"],
                        "lost_packets": result["lost_packets"],
                        "loss_rate_pct": result["loss_rate"],
                        "throughput_mbps": result["throughput_mbps"],
                        "avg_delay_ms": result["avg_delay_ms"],
                        "avg_jitter_ms": result["avg_jitter_ms"],
                    })

    write_csv(os.path.join(OUTPUT_DIR, "resumo_simulacoes.csv"), simulation_rows)
    write_csv(os.path.join(OUTPUT_DIR, "metricas_fluxos.csv"), flow_rows)

    aggregate_rows = []
    metrics = ("throughput_mbps", "loss_rate_pct", "avg_delay_ms", "avg_jitter_ms", "jain_fairness")
    for experiment in EXPERIMENTS:
        alpha, gamma = experiment.split("_")
        for delay in DELAYS:
            selected = [
                row for row in simulation_rows
                if row["experiment"] == experiment and row["delay_ms"] == delay
            ]
            for metric in metrics:
                stats = confidence_summary([row.get(metric) for row in selected])
                aggregate_rows.append({
                    "experiment": experiment,
                    "alpha": alpha[1:],
                    "gamma": gamma[1:],
                    "baseline": alpha == "A0.25" and gamma == "G0.05",
                    "delay_ms": delay,
                    "metric": metric,
                    **stats,
                })
    write_csv(os.path.join(OUTPUT_DIR, "resumo_estatistico_95ic.csv"), aggregate_rows)

    report_path = os.path.join(OUTPUT_DIR, "relatorio_validacao.txt")
    with open(report_path, "w", encoding="utf-8") as report:
        report.write("RELATORIO DA CAMPANHA FATORIAL ALPHA/GAMMA\n")
        report.write("=" * 52 + "\n")
        report.write(f"Grade: {len(ALPHAS)} x {len(GAMMAS)} = {len(EXPERIMENTS)} combinações\n")
        report.write("Alpha: 0.10, 0.25, 0.50\n")
        report.write("Gamma: 0.00, 0.05, 0.10\n")
        report.write("Baseline definida a priori: Alpha=0.25, Gamma=0.05\n")
        report.write(f"Simulações esperadas: {expected}\n")
        report.write(f"Simulações analisadas: {len(simulation_rows)}\n")
        report.write(f"Fluxos registrados: {len(flow_rows)}\n")
        report.write(f"Ocorrências estruturais: {len(warnings)}\n\n")
        report.write(
            "ATENÇÃO: média, desvio-padrão e IC95% descrevem as execuções fornecidas. "
            "Não demonstram independência estatística se as sementes não alterarem "
            "fontes aleatórias efetivamente utilizadas pelo simulador.\n"
        )
        report.write(
            "O IC usa t de Student para n<=30. Com menos de duas execuções válidas, "
            "desvio-padrão e intervalo de confiança não são calculados.\n\n"
        )
        if warnings:
            report.write("OCORRÊNCIAS:\n")
            for warning in warnings:
                report.write(f"- {warning}\n")
        else:
            report.write("Nenhuma ausência estrutural detectada.\n")

    print(f"Simulações: {len(simulation_rows)}/{expected}")
    print(f"Fluxos: {len(flow_rows)}")
    print(f"Ocorrências: {len(warnings)}")
    print(f"Saída: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
