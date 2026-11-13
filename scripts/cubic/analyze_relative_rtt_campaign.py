#!/usr/bin/env python3
"""
Analisa a campanha relative_rtt_adaptation_initial do ns-3.

Gera:
  results/relative_rtt_adaptation_initial/analysis/
    resumo_simulacoes.csv
    metricas_fluxos.csv
    series_temporais.csv
    relatorio_validacao.txt
    graficos/comparativo_*.png
    graficos/temporal_*.png

Uso:
  python3 scripts/cubic/analyze_relative_rtt_campaign.py
  python3 scripts/cubic/analyze_relative_rtt_campaign.py --input results/relative_rtt_adaptation_initial
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

UINT32_MAX = 4294967295
ALGORITHMS = ("Cubic", "Bbr", "CubicRtt")
DELAYS = (10, 50, 100)
RUNS = range(1, 6)
# Cada fluxo de dados usa a porta de destino 50000.
SOURCE_TO_FLOW = {
    "10.0.1.1": 0,
    "10.0.2.1": 1,
    "10.0.3.1": 2,
    "10.0.4.1": 3,
}
LABELS = {"Cubic": "CUBIC", "Bbr": "BBR", "CubicRtt": "CUBIC-RTT"}
METRICS = {
    "cwnd": ("CWND", "bytes"),
    "rtt": ("RTT", "ms"),
    "ssth": ("SSTHRESH", "bytes"),
    "inflight": ("Bytes em voo", "bytes"),
}
BIN_SECONDS = 0.5


def parse_ns(value: str) -> float:
    return float(value.replace("+", "").replace("ns", ""))


def read_trace(path: Path, metric: str):
    points = []
    if not path.exists():
        return points
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                t, value = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            if metric == "rtt":
                if value <= 0:
                    continue
                value *= 1000.0  # segundos -> ms
            elif metric == "ssth":
                # UINT32_MAX é o sentinel de "sem limiar definido".
                if value <= 0 or value >= UINT32_MAX:
                    continue
            elif metric == "cwnd":
                if value < 0:
                    continue
            elif metric == "inflight":
                if value < 0:
                    continue
            points.append((t, value))
    return points


def parse_flowmonitor(path: Path):
    root = ET.parse(path).getroot()
    classifier = root.find(".//Ipv4FlowClassifier")
    forward = {}
    if classifier is not None:
        for flow in classifier.findall("Flow"):
            if flow.attrib.get("destinationPort") == "50000":
                forward[flow.attrib["flowId"]] = flow.attrib

    stats = root.find(".//FlowStats")
    rows = []
    if stats is None:
        return rows

    for flow in stats.findall("Flow"):
        flow_id = flow.attrib["flowId"]
        info = forward.get(flow_id)
        if info is None:
            continue
        tx_bytes = int(flow.attrib.get("txBytes", 0))
        rx_bytes = int(flow.attrib.get("rxBytes", 0))
        tx_packets = int(flow.attrib.get("txPackets", 0))
        rx_packets = int(flow.attrib.get("rxPackets", 0))
        lost = int(flow.attrib.get("lostPackets", 0))
        delay_sum_ns = parse_ns(flow.attrib.get("delaySum", "+0ns"))
        jitter_sum_ns = parse_ns(flow.attrib.get("jitterSum", "+0ns"))
        first_rx = parse_ns(flow.attrib.get("timeFirstRxPacket", "+0ns"))
        last_rx = parse_ns(flow.attrib.get("timeLastRxPacket", "+0ns"))
        duration = (last_rx - first_rx) / 1e9
        throughput = rx_bytes * 8 / duration / 1e6 if duration > 0 else 0.0
        rows.append({
            "flowmonitor_id": int(flow_id),
            "source": info.get("sourceAddress", ""),
            "destination": info.get("destinationAddress", ""),
            "tx_bytes": tx_bytes, "rx_bytes": rx_bytes,
            "tx_packets": tx_packets, "rx_packets": rx_packets,
            "lost_packets": lost,
            "loss_rate_pct": lost / tx_packets * 100 if tx_packets else 0.0,
            "throughput_mbps": throughput,
            "avg_delay_ms": delay_sum_ns / rx_packets / 1e6 if rx_packets else 0.0,
            "avg_jitter_ms": jitter_sum_ns / (rx_packets - 1) / 1e6 if rx_packets > 1 else 0.0,
            "first_rx_ns": first_rx, "last_rx_ns": last_rx,
        })
    return rows


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize_flows(flows):
    if not flows:
        return {}
    tx_bytes = sum(x["tx_bytes"] for x in flows)
    rx_bytes = sum(x["rx_bytes"] for x in flows)
    tx_packets = sum(x["tx_packets"] for x in flows)
    rx_packets = sum(x["rx_packets"] for x in flows)
    lost = sum(x["lost_packets"] for x in flows)
    first_rx = min(x["first_rx_ns"] for x in flows)
    last_rx = max(x["last_rx_ns"] for x in flows)
    duration = (last_rx - first_rx) / 1e9
    delay_ms = (
        sum(x["avg_delay_ms"] * x["rx_packets"] for x in flows) / rx_packets
        if rx_packets else 0.0
    )
    jitter_n = sum(max(x["rx_packets"] - 1, 0) for x in flows)
    jitter_ms = (
        sum(x["avg_jitter_ms"] * max(x["rx_packets"] - 1, 0) for x in flows) / jitter_n
        if jitter_n else 0.0
    )
    return {
        "data_flows": len(flows),
        "tx_bytes": tx_bytes, "rx_bytes": rx_bytes,
        "tx_packets": tx_packets, "rx_packets": rx_packets,
        "lost_packets": lost,
        "throughput_mbps": rx_bytes * 8 / duration / 1e6 if duration > 0 else 0.0,
        "loss_rate_pct": lost / tx_packets * 100 if tx_packets else 0.0,
        "avg_delay_ms": delay_ms, "avg_jitter_ms": jitter_ms,
    }


def temporal_bins(points, bin_width=BIN_SECONDS):
    buckets = defaultdict(list)
    for t, value in points:
        buckets[int(t // bin_width)].append(value)
    return {index * bin_width: statistics.mean(vals) for index, vals in buckets.items()}


def main():
    parser = argparse.ArgumentParser(description="Consolida e gera gráficos da campanha inicial CUBIC/BBR/CUBIC-RTT.")
    parser.add_argument("--input", default="results/relative_rtt_adaptation_initial",
                        help="Diretório raiz dos resultados da campanha.")
    parser.add_argument("--bin", type=float, default=BIN_SECONDS,
                        help="Largura, em segundos, dos intervalos dos gráficos temporais (padrão: 0.5).")
    args = parser.parse_args()

    project = Path(__file__).resolve().parents[2]
    input_dir = (project / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    output_dir = input_dir / "analysis"
    graph_dir = output_dir / "graficos"
    graph_dir.mkdir(parents=True, exist_ok=True)

    simulation_rows, flow_rows, warnings = [], [], []
    # chave temporal: algoritmo/atraso/métrica/tempo -> amostras de todas as runs e fluxos
    temporal = defaultdict(list)
    expected = len(ALGORITHMS) * len(DELAYS) * len(RUNS)

    for algorithm in ALGORITHMS:
        for delay in DELAYS:
            for run in RUNS:
                run_dir = input_dir / algorithm / f"atraso_{delay}" / f"run_{run}"
                xml = run_dir / "CubicExperiment.flowmonitor"
                if not xml.is_file():
                    warnings.append(f"FlowMonitor ausente: {xml}")
                    continue
                try:
                    flows = parse_flowmonitor(xml)
                except Exception as exc:
                    warnings.append(f"Erro no XML {xml}: {exc}")
                    continue

                # O classifier identifica os quatro fluxos de dados (porta destino 50000).
                flows = [f for f in flows if f["source"] in SOURCE_TO_FLOW]
                summary = summarize_flows(flows)
                if len(flows) != 4:
                    warnings.append(f"{algorithm}, {delay}ms, run {run}: {len(flows)} fluxos de dados; esperado 4.")

                simulation_rows.append({
                    "algorithm": algorithm, "delay_ms": delay, "repetition": run, **summary
                })

                for flow in flows:
                    index = SOURCE_TO_FLOW[flow["source"]]
                    row = {
                        "algorithm": algorithm, "delay_ms": delay, "repetition": run,
                        "tcp_flow_index": index, **flow
                    }
                    for metric in METRICS:
                        trace = run_dir / f"CubicExperiment-flow{index}-{metric}.data"
                        points = read_trace(trace, metric)
                        values = [v for _, v in points]
                        row[f"{metric}_samples"] = len(values)
                        row[f"{metric}_mean"] = statistics.mean(values) if values else ""
                        row[f"{metric}_min"] = min(values) if values else ""
                        row[f"{metric}_max"] = max(values) if values else ""
                        binned = temporal_bins(points, args.bin)
                        for t, value in binned.items():
                            temporal[(algorithm, delay, metric, t)].append(value)
                        if not trace.is_file():
                            warnings.append(f"Trace ausente: {trace}")
                    flow_rows.append(row)

    write_csv(output_dir / "resumo_simulacoes.csv", simulation_rows)
    write_csv(output_dir / "metricas_fluxos.csv", flow_rows)

    temporal_rows = []
    for (algorithm, delay, metric, t), values in sorted(temporal.items()):
        temporal_rows.append({
            "algorithm": algorithm, "delay_ms": delay, "metric": metric,
            "time_s": t, "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "samples": len(values),
        })
    write_csv(output_dir / "series_temporais.csv", temporal_rows)

    report = [
        "RELATORIO DE ANALISE — CAMPANHA INICIAL",
        "=" * 55,
        f"Diretório: {input_dir}",
        f"Simulações encontradas: {len(simulation_rows)}/{expected}",
        f"Fluxos de dados registrados: {len(flow_rows)}/{expected * 4}",
        "Critério: somente fluxos TCP com destinationPort=50000.",
        "Os fluxos reversos (ACKs) não entram na vazão da aplicação.",
        "RTT convertido de segundos para milissegundos.",
        "SSTHRESH: valores 0 e UINT32_MAX removidos dos resumos/gráficos.",
        f"Agregação temporal: bins de {args.bin:g} segundo(s), média entre fluxos e repetições disponíveis.",
        f"Ocorrências: {len(warnings)}",
        "",
    ]
    report += ["AVISOS:"] + ([f"- {w}" for w in warnings] if warnings else ["Nenhum."])
    (output_dir / "relatorio_validacao.txt").write_text("\n".join(report) + "\n", encoding="utf-8")

    # Importar matplotlib somente depois de consolidar CSVs.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("CSV gerados, mas matplotlib não está instalado. Instale: python3 -m pip install matplotlib")
        print(f"Saída: {output_dir}")
        return

    labels = LABELS
    colors = {"Cubic": "tab:blue", "Bbr": "tab:orange", "CubicRtt": "tab:green"}
    compare_metrics = [
        ("throughput_mbps", "Vazão agregada", "Vazão (Mbps)", "throughput"),
        ("loss_rate_pct", "Taxa de perda", "Pacotes perdidos (%)", "perda"),
        ("avg_delay_ms", "Atraso médio", "Atraso (ms)", "atraso"),
        ("avg_jitter_ms", "Jitter médio", "Jitter (ms)", "jitter"),
    ]

    for column, title, ylabel, filename in compare_metrics:
        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        for algorithm in ALGORITHMS:
            xs, means, errors = [], [], []
            for delay in DELAYS:
                vals = [r[column] for r in simulation_rows
                        if r["algorithm"] == algorithm and r["delay_ms"] == delay and column in r]
                if vals:
                    xs.append(delay)
                    means.append(statistics.mean(vals))
                    errors.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
            if xs:
                ax.errorbar(xs, means, yerr=errors, marker="o", capsize=4,
                            linewidth=2, label=labels[algorithm], color=colors[algorithm])
        ax.set_title(f"{title} — campanha inicial")
        ax.set_xlabel("Atraso configurado no gargalo (ms)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(DELAYS)
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(graph_dir / f"comparativo_{filename}.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

    # Curvas temporais: média por intervalo entre fluxos e repetições disponíveis.
    for metric, (title, unit) in METRICS.items():
        for delay in DELAYS:
            fig, ax = plt.subplots(figsize=(10, 5.5))
            plotted = False
            for algorithm in ALGORITHMS:
                subset = [(t, vals) for (alg, d, m, t), vals in temporal.items()
                          if alg == algorithm and d == delay and m == metric]
                if not subset:
                    continue
                subset.sort()
                xs = [t for t, _ in subset]
                means = [statistics.mean(vals) for _, vals in subset]
                stds = [statistics.stdev(vals) if len(vals) > 1 else 0.0 for _, vals in subset]
                ax.plot(xs, means, label=labels[algorithm], color=colors[algorithm], linewidth=1.6)
                lower = [m - s for m, s in zip(means, stds)]
                upper = [m + s for m, s in zip(means, stds)]
                ax.fill_between(xs, lower, upper, color=colors[algorithm], alpha=0.12)
                plotted = True
            if plotted:
                ax.set_title(f"{title} ao longo do tempo — gargalo {delay} ms")
                ax.set_xlabel("Tempo de simulação (s)")
                ax.set_ylabel(f"{title} ({unit})")
                ax.grid(True, alpha=0.3)
                ax.legend()
                fig.tight_layout()
                fig.savefig(graph_dir / f"temporal_{metric}_{delay}ms.png", dpi=180, bbox_inches="tight")
            plt.close(fig)

    print("\nANÁLISE CONCLUÍDA")
    print(f"Simulações: {len(simulation_rows)}/{expected}")
    print(f"Fluxos de dados: {len(flow_rows)}/{expected * 4}")
    print(f"Gráficos: {graph_dir}")
    print(f"CSVs e relatório: {output_dir}")
    print(f"Avisos: {len(warnings)}")
    if warnings:
        print("Consulte relatorio_validacao.txt")


if __name__ == "__main__":
    main()
