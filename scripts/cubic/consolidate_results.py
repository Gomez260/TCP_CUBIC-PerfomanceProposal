import csv
import os
import sys

import analyze_results as analyzer


PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)

DELAYS = (10, 50, 100)
RUNS = range(1, 6)
ALGORITHMS = ("Cubic", "Bbr", "CubicRtt")

UINT32_MAX = 4294967295

SOURCE_TO_TCP_FLOW = {
    "10.0.1.1": 0,
    "10.0.2.1": 1,
    "10.0.3.1": 2,
    "10.0.4.1": 3,
}



def metric_stats(results_dir, flow_index, metric, scale=1):
    filename = os.path.join(
        results_dir,
        f"CubicExperiment-flow{flow_index}-{metric}.data"
    )

    if not os.path.exists(filename):
        return None, filename

    data = analyzer.analyze_data_file(filename)

    # Detecta o sentinel antes de filtrar os valores.
    uint32_max = any(value >= UINT32_MAX for _, value in data)
    sentinel_samples = sum(
        1 for _, value in data if value >= UINT32_MAX
    )

    if metric == "inflight":
        # Zero é um estado válido de BytesInFlight.
        values = [value * scale for _, value in data]

    elif metric == "ssth":
        # Ignora zero, como antes, e remove o sentinel UINT32_MAX.
        values = [
            value * scale
            for _, value in data
            if 0 < value < UINT32_MAX
        ]

    else:
        # Mantém o comportamento anterior para CWND e RTT.
        values = [
            value * scale
            for _, value in data
            if value > 0
        ]

    if not values:
        return None, filename

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "samples": len(values),
        "uint32_max": uint32_max,
        "sentinel_samples": sentinel_samples
    }, filename


def calculate_summary(results):
    if not results:
        return {}

    total_tx = sum(r["tx_bytes"] for r in results)
    total_rx = sum(r["rx_bytes"] for r in results)
    total_tx_packets = sum(r["tx_packets"] for r in results)
    total_lost = sum(r["lost_packets"] for r in results)
    total_rx_packets = sum(r["rx_packets"] for r in results)

    first_rx = min(r["first_rx_ns"] for r in results)
    last_rx = max(r["last_rx_ns"] for r in results)

    duration = (last_rx - first_rx) / 1e9

    throughput = (
        total_rx * 8 / duration / 1e6
        if duration > 0 else 0
    )

    loss_rate = (
        total_lost / total_tx_packets * 100
        if total_tx_packets > 0 else 0
    )

    avg_delay = (
        sum(r["avg_delay_ms"] * r["rx_packets"] for r in results)
        / total_rx_packets
        if total_rx_packets > 0 else 0
    )

    jitter_samples = sum(
        max(r["rx_packets"] - 1, 0) for r in results
    )

    avg_jitter = (
        sum(
            r["avg_jitter_ms"] * max(r["rx_packets"] - 1, 0)
            for r in results
        ) / jitter_samples
        if jitter_samples > 0 else 0
    )

    return {
        "flows": len(results),
        "tx_bytes": total_tx,
        "rx_bytes": total_rx,
        "tx_packets": total_tx_packets,
        "rx_packets": total_rx_packets,
        "lost_packets": total_lost,
        "throughput_mbps": throughput,
        "loss_rate_pct": loss_rate,
        "avg_delay_ms": avg_delay,
        "avg_jitter_ms": avg_jitter
    }


def write_csv(filename, rows):
    if not rows:
        return

    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    output_dir = os.path.join(PROJECT_DIR, "results", "consolidated")
    os.makedirs(output_dir, exist_ok=True)

    simulation_rows = []
    flow_rows = []
    warnings = []

    expected_simulations = len(ALGORITHMS) * len(DELAYS) * len(RUNS)

    for algorithm in ALGORITHMS:
        for delay in DELAYS:
            for run in RUNS:

                results_dir = os.path.join(
                    PROJECT_DIR,
                    "results",
                    algorithm,
                    f"atraso_{delay}",
                    f"run_{run}"
                )

                flowmonitor = os.path.join(
                    results_dir,
                    "CubicExperiment.flowmonitor"
                )

                if not os.path.exists(flowmonitor):
                    warnings.append(
                        f"Arquivo FlowMonitor ausente: {flowmonitor}"
                    )
                    continue

                try:
                    results = analyzer.parse_flowmonitor(flowmonitor)
                except Exception as error:
                    warnings.append(
                        f"Erro lendo {flowmonitor}: {error}"
                    )
                    continue

                summary = calculate_summary(results)

                simulation = {
                    "algorithm": algorithm,
                    "delay_ms": delay,
                    "repetition": run,
                    **summary
                }

                cwnd_anomaly_flows = []
                ssth_max_flows = []

                for result in results:

                    source = result["source"]
                    tcp_flow = SOURCE_TO_TCP_FLOW.get(source)

                    if tcp_flow is None:
                        warnings.append(
                            f"Origem sem mapeamento: {source} "
                            f"em {algorithm}, {delay}ms, run {run}"
                        )
                        continue

                    metrics = {}

                    for metric, scale in (
                        ("cwnd", 1),
                        ("rtt", 1000),
                        ("inflight", 1),
                        ("ssth", 1)
                    ):
                        stats, filename = metric_stats(
                            results_dir,
                            tcp_flow,
                            metric,
                            scale
                        )

                        if stats is None:
                            warnings.append(
                                f"Métrica ausente ou vazia: {filename}"
                            )
                            metrics[metric] = {}
                        else:
                            metrics[metric] = stats

                    cwnd = metrics["cwnd"]
                    rtt = metrics["rtt"]
                    inflight = metrics["inflight"]
                    ssth = metrics["ssth"]

                    if cwnd.get("uint32_max", False):
                        cwnd_anomaly_flows.append(tcp_flow)

                    if ssth.get("uint32_max", False):
                        ssth_max_flows.append(tcp_flow)

                    flow_rows.append({
                        "algorithm": algorithm,
                        "delay_ms": delay,
                        "repetition": run,
                        "flowmonitor_id": result["flow"],
                        "tcp_flow_index": tcp_flow,
                        "source": source,
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
                        "cwnd_min_bytes": cwnd.get("min"),
                        "cwnd_max_bytes": cwnd.get("max"),
                        "cwnd_avg_bytes": cwnd.get("avg"),
                        "cwnd_samples": cwnd.get("samples"),
                        "cwnd_uint32_max": cwnd.get("uint32_max"),
                        "rtt_min_ms": rtt.get("min"),
                        "rtt_max_ms": rtt.get("max"),
                        "rtt_avg_ms": rtt.get("avg"),
                        "rtt_samples": rtt.get("samples"),
                        "inflight_min_bytes": inflight.get("min"),
                        "inflight_max_bytes": inflight.get("max"),
                        "inflight_avg_bytes": inflight.get("avg"),
                        "inflight_samples": inflight.get("samples"),
                        "ssth_min_bytes": ssth.get("min"),
                        "ssth_max_bytes": ssth.get("max"),
                        "ssth_avg_bytes": ssth.get("avg"),
                        "ssth_samples": ssth.get("samples"),
                        "ssth_uint32_max": ssth.get("uint32_max"),
                        "ssth_sentinel_samples": ssth.get("sentinel_samples", 0)
                    })

                simulation["cwnd_uint32_max_flows"] = len(cwnd_anomaly_flows)
                simulation["ssth_uint32_max_flows"] = len(ssth_max_flows)
                simulation["ssth_sentinel_samples"] = sum(
                row.get("ssth_sentinel_samples", 0)
                for row in flow_rows
                if row["algorithm"] == algorithm
                and row["delay_ms"] == delay
                 and row["repetition"] == run
                 )

                simulation_rows.append(simulation)

                if len(results) != 4:
                    warnings.append(
                        f"{algorithm}, {delay}ms, run {run}: "
                        f"{len(results)} fluxos encontrados; esperado: 4"
                    )

    simulation_file = os.path.join(
        output_dir, "resumo_simulacoes.csv"
    )

    flow_file = os.path.join(
        output_dir, "metricas_fluxos.csv"
    )

    report_file = os.path.join(
        output_dir, "relatorio_validacao.txt"
    )

    write_csv(simulation_file, simulation_rows)
    write_csv(flow_file, flow_rows)

    with open(report_file, "w", encoding="utf-8") as report:
        report.write("RELATORIO DE CONSOLIDACAO DOS RESULTADOS\n")
        report.write("=" * 50 + "\n\n")

        report.write(
            f"Simulacoes esperadas: {expected_simulations}\n"
        )
        report.write(
            f"Simulacoes encontradas: {len(simulation_rows)}\n"
        )
        report.write(
            f"Fluxos registrados: {len(flow_rows)}\n"
        )
        report.write(
            f"Fluxos esperados: {expected_simulations * 4}\n"
        )
        report.write(
            f"Ocorrencias para verificacao: {len(warnings)}\n\n"
        )

        if warnings:
            report.write("OCORRENCIAS:\n")
            for warning in warnings:
                report.write(f"- {warning}\n")
        else:
            report.write("Nenhuma ausencia ou inconsistência estrutural detectada.\n")

    print("CONSOLIDACAO CONCLUIDA")
    print(f"Simulacoes: {len(simulation_rows)}/{expected_simulations}")
    print(f"Fluxos: {len(flow_rows)}/{expected_simulations * 4}")
    print(f"Ocorrencias: {len(warnings)}")
    print()
    print(f"Arquivo: {simulation_file}")
    print(f"Arquivo: {flow_file}")
    print(f"Relatorio: {report_file}")


if __name__ == "__main__":
    main()
