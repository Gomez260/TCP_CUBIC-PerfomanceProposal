import csv
import os
import sys

import consolidate_results as base


PROJECT_DIR = base.PROJECT_DIR
INPUT_DIR = os.path.join(
    PROJECT_DIR, "results", "parameter_experiments"
)
OUTPUT_DIR = os.path.join(INPUT_DIR, "consolidated")

EXPERIMENTS = (
    "A0.10_G0.00",
    "A0.10_G0.025",
    "A0.10_G0.05",
    "A0.10_G0.10",
    "A0.25_G0.00",
    "A0.25_G0.025",
    "A0.50_G0.00",
    "A0.50_G0.025",
    "A0.75_G0.00",
    "A0.75_G0.025",
    "A0.75_G0.05",
    "A0.75_G0.10",
)
DELAYS = (10, 50, 100)
RUNS = range(1, 6)


def write_csv(filename, rows):
    if not rows:
        return

    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def find_run_dir(experiment, delay, run):
    candidates = [
        os.path.join(INPUT_DIR, experiment, f"{delay}ms", f"run{run}"),
        os.path.join(INPUT_DIR, experiment, f"{delay}ms", f"run_{run}"),
        os.path.join(INPUT_DIR, experiment, f"atraso_{delay}", f"run{run}"),
        os.path.join(INPUT_DIR, experiment, f"atraso_{delay}", f"run_{run}"),
    ]

    for path in candidates:
        if os.path.isdir(path):
            return path

    return candidates[0]


def calculate_jain(results):
    if not results:
        return None

    first_rx = min(r["first_rx_ns"] for r in results)
    last_rx = max(r["last_rx_ns"] for r in results)
    duration = (last_rx - first_rx) / 1e9

    if duration <= 0:
        return None

    throughputs = [
        r["rx_bytes"] * 8 / duration / 1e6
        for r in results
    ]

    total = sum(throughputs)
    squares = sum(value ** 2 for value in throughputs)
    n = len(throughputs)

    if squares == 0:
        return None

    return (total ** 2) / (n * squares)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    simulation_rows = []
    flow_rows = []
    warnings = []

    expected = len(EXPERIMENTS) * len(DELAYS) * len(RUNS)

    for experiment in EXPERIMENTS:
        for delay in DELAYS:
            for run in RUNS:
                results_dir = find_run_dir(experiment, delay, run)
                flowmonitor = os.path.join(
                    results_dir, "CubicExperiment.flowmonitor"
                )

                if not os.path.exists(flowmonitor):
                    warnings.append(
                        f"FlowMonitor ausente: {flowmonitor}"
                    )
                    continue

                try:
                    results = base.analyzer.parse_flowmonitor(flowmonitor)
                except Exception as error:
                    warnings.append(
                        f"Erro lendo {flowmonitor}: {error}"
                    )
                    continue

                summary = base.calculate_summary(results)
                jain = calculate_jain(results)

                simulation_rows.append({
                    "experiment": experiment,
                    "delay_ms": delay,
                    "repetition": run,
                    **summary,
                    "jain_fairness": jain
                })

                if len(results) != 4:
                    warnings.append(
                        f"{experiment}, {delay}ms, run {run}: "
                        f"{len(results)} fluxos encontrados; esperado: 4"
                    )

                for result in results:
                    tcp_flow = base.SOURCE_TO_TCP_FLOW.get(
                        result["source"]
                    )

                    if tcp_flow is None:
                        warnings.append(
                            f"Origem sem mapeamento: {result['source']} "
                            f"em {experiment}, {delay}ms, run {run}"
                        )
                        continue

                    metrics = {}

                    for metric, scale in (
                        ("cwnd", 1),
                        ("rtt", 1000),
                        ("inflight", 1),
                        ("ssth", 1)
                    ):
                        stats, filename = base.metric_stats(
                            results_dir, tcp_flow, metric, scale
                        )

                        if stats is None:
                            warnings.append(
                                f"Métrica ausente ou vazia: {filename}"
                            )
                            metrics[metric] = {}
                        else:
                            metrics[metric] = stats

                    flow_rows.append({
                        "experiment": experiment,
                        "delay_ms": delay,
                        "repetition": run,
                        "flow": tcp_flow,
                        "source": result["source"],
                        "destination": result["destination"],
                        "tx_bytes": result["tx_bytes"],
                        "rx_bytes": result["rx_bytes"],
                        "tx_packets": result["tx_packets"],
                        "rx_packets": result["rx_packets"],
                        "lost_packets": result["lost_packets"],
                        "loss_rate_pct": result["loss_rate"],
                        "avg_delay_ms": result["avg_delay_ms"],
                        "avg_jitter_ms": result["avg_jitter_ms"],
                        "cwnd_min_bytes": metrics["cwnd"].get("min"),
                        "cwnd_avg_bytes": metrics["cwnd"].get("avg"),
                        "cwnd_max_bytes": metrics["cwnd"].get("max"),
                        "rtt_min_ms": metrics["rtt"].get("min"),
                        "rtt_avg_ms": metrics["rtt"].get("avg"),
                        "rtt_max_ms": metrics["rtt"].get("max"),
                        "inflight_avg_bytes": metrics["inflight"].get("avg"),
                        "ssth_avg_bytes": metrics["ssth"].get("avg")
                    })

    write_csv(
        os.path.join(OUTPUT_DIR, "resumo_simulacoes.csv"),
        simulation_rows
    )
    write_csv(
        os.path.join(OUTPUT_DIR, "metricas_fluxos.csv"),
        flow_rows
    )

    report_path = os.path.join(
        OUTPUT_DIR, "relatorio_validacao.txt"
    )

    with open(report_path, "w", encoding="utf-8") as report:
        report.write("RELATORIO DOS EXPERIMENTOS DE PARAMETROS\n")
        report.write("=" * 50 + "\n\n")
        report.write(f"Simulacoes esperadas: {expected}\n")
        report.write(f"Simulacoes encontradas: {len(simulation_rows)}\n")
        report.write(f"Fluxos registrados: {len(flow_rows)}\n")
        report.write(f"Fluxos esperados: {expected * 4}\n")
        report.write(f"Ocorrencias: {len(warnings)}\n\n")

        for warning in warnings:
            report.write(f"- {warning}\n")

        if not warnings:
            report.write("Nenhuma ocorrencia estrutural detectada.\n")

    print("ANALISE CONCLUIDA")
    print(f"Simulacoes: {len(simulation_rows)}/{expected}")
    print(f"Fluxos: {len(flow_rows)}/{expected * 4}")
    print(f"Ocorrencias: {len(warnings)}")
    print(f"\nResultados em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
