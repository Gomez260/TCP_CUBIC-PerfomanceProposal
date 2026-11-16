#!/usr/bin/env python3
"""
Gera graficos das campanhas Parameters, Robustness e Coexistence.

Uso:
    python3 scripts/cubic/plot_results.py
    python3 scripts/cubic/plot_results.py --campaign parameters
    python3 scripts/cubic/plot_results.py --campaign robustness
    python3 scripts/cubic/plot_results.py --campaign coexistence

Os graficos PNG e PDF sao salvos em results/graficos/<campanha>/.
"""

import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as error:
    print("Dependencias ausentes. Instale com: pip install matplotlib numpy", file=sys.stderr)
    raise SystemExit(1) from error

try:
    from analyze_results import parse_flowmonitor, analyze_data_file
except ImportError as error:
    print("Execute este script a partir do repositorio, preservando scripts/cubic/analyze_results.py.", file=sys.stderr)
    raise SystemExit(1) from error


PROJECT_DIR = Path(__file__).resolve().parents[2]
PARAMETERS_DIR = PROJECT_DIR / "results" / "fixed_parameter_campaign"
ROBUSTNESS_DIR = Path("/mnt/d/TCC-results/robustness_experiments")
COEXISTENCE_DIR = Path("/mnt/d/TCC-results/coexistence_experiments")
OUTPUT_DIR = PROJECT_DIR / "results" / "graficos"

METRICS = (
    ("throughput_mbps", "Vazao agregada", "Vazao (Mbps)"),
    ("avg_delay_ms", "Atraso medio", "Atraso (ms)"),
    ("avg_jitter_ms", "Jitter medio", "Jitter (ms)"),
    ("loss_rate_pct", "Taxa de pacotes perdidos no FlowMonitor", "Pacotes perdidos (%)"),
    ("jain_fairness", "Indice de justica de Jain", "Indice de Jain"),
)

ALGORITHM_LABELS = {
    "cubic": "CUBIC",
    "adaptive": "Adaptive",
    "fixed": "Fixed",
    "TcpCubic": "CUBIC",
    "TcpBbr": "BBR",
}


def numeric(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def mean_std(values):
    clean = [value for value in values if value is not None]
    if not clean:
        return None, None
    average = sum(clean) / len(clean)
    if len(clean) < 2:
        return average, 0.0
    variance = sum((value - average) ** 2 for value in clean) / (len(clean) - 1)
    return average, math.sqrt(variance)


def save_figure(fig, output_dir, filename):
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for extension in ("png", "pdf"):
        destination = output_dir / f"{filename}.{extension}"
        fig.savefig(destination, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {output_dir / filename}.png")
    print(f"[OK] {output_dir / filename}.pdf")


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def jain_index(flows):
    rates = [numeric(flow.get("throughput_mbps")) for flow in flows]
    rates = [rate for rate in rates if rate is not None]
    if not rates:
        return None
    total = sum(rates)
    squares = sum(rate * rate for rate in rates)
    if squares == 0:
        return None
    return total * total / (len(rates) * squares)


def summarize_flows(flows):
    if not flows:
        return None

    total_tx_packets = sum(flow["tx_packets"] for flow in flows)
    total_lost = sum(flow["lost_packets"] for flow in flows)
    total_rx_packets = sum(flow["rx_packets"] for flow in flows)
    total_rx_bytes = sum(flow["rx_bytes"] for flow in flows)
    first_rx = min(flow["first_rx_ns"] for flow in flows)
    last_rx = max(flow["last_rx_ns"] for flow in flows)
    duration = (last_rx - first_rx) / 1e9

    throughput = total_rx_bytes * 8 / duration / 1e6 if duration > 0 else None
    loss = total_lost / total_tx_packets * 100 if total_tx_packets else None
    delay = (
        sum(flow["avg_delay_ms"] * flow["rx_packets"] for flow in flows) / total_rx_packets
        if total_rx_packets else None
    )
    jitter_samples = sum(max(flow["rx_packets"] - 1, 0) for flow in flows)
    jitter = (
        sum(flow["avg_jitter_ms"] * max(flow["rx_packets"] - 1, 0) for flow in flows) / jitter_samples
        if jitter_samples else None
    )

    return {
        "throughput_mbps": throughput,
        "loss_rate_pct": loss,
        "avg_delay_ms": delay,
        "avg_jitter_ms": jitter,
        "jain_fairness": jain_index(flows),
        "flows": len(flows),
        "tx_packets": total_tx_packets,
        "rx_packets": total_rx_packets,
        "lost_packets": total_lost,
    }


def parse_parameters_metadata(xml_path, root):
    relative = xml_path.relative_to(root)
    parts = relative.parts
    # Estrutura esperada: <cenario>/<banda>/<atraso>/<algoritmo>/run_N/arquivo.flowmonitor
    if len(parts) < 6:
        return None
    scenario, bandwidth, delay, algorithm = parts[-6], parts[-5], parts[-4], parts[-3]
    delay_match = re.search(r"(\d+(?:\.\d+)?)\s*ms", delay, re.IGNORECASE)
    bandwidth_match = re.search(r"(\d+(?:\.\d+)?)\s*Mbps", bandwidth, re.IGNORECASE)
    run_match = re.search(r"run[_-]?(\d+)", parts[-2], re.IGNORECASE)
    if not delay_match or not bandwidth_match or algorithm.lower() not in ("cubic", "adaptive", "fixed"):
        return None
    return {
        "scenario": scenario,
        "bandwidth_mbps": float(bandwidth_match.group(1)),
        "bandwidth_label": bandwidth,
        "delay_ms": float(delay_match.group(1)),
        "algorithm": algorithm.lower(),
        "repetition": int(run_match.group(1)) if run_match else parts[-2],
    }


def load_flowmonitor_rows(root, metadata_parser):
    rows = []
    warnings = []
    if not root.is_dir():
        print(f"[AVISO] Diretorio nao encontrado: {root}")
        return rows

    files = sorted(root.rglob("*.flowmonitor"))
    for xml_path in files:
        metadata = metadata_parser(xml_path, root)
        if metadata is None:
            warnings.append(f"Estrutura nao reconhecida: {xml_path}")
            continue
        try:
            flows = parse_flowmonitor(str(xml_path))
            summary = summarize_flows(flows)
            if summary is None:
                warnings.append(f"Nenhum fluxo TCP de dados identificado: {xml_path}")
                continue
            rows.append({**metadata, **summary, "source_file": str(xml_path)})
        except Exception as error:
            warnings.append(f"Falha ao ler {xml_path}: {error}")

    print(f"[INFO] {root}: {len(rows)} simulacao(oes) analisada(s) de {len(files)} XML(s).")
    if warnings:
        print(f"[AVISO] {len(warnings)} arquivo(s) ignorado(s). Primeiro aviso: {warnings[0]}")
    return rows


def plot_parameter_campaign(root, output_dir):
    rows = load_flowmonitor_rows(root, parse_parameters_metadata)
    if not rows:
        print("[AVISO] Nenhum resultado valido encontrado para Parameters.")
        return 0

    write_csv(output_dir / "resumo_parameters.csv", rows)
    generated = 0
    groups = sorted({(row["scenario"], row["bandwidth_label"]) for row in rows})

    for scenario, bandwidth in groups:
        subset = [row for row in rows if row["scenario"] == scenario and row["bandwidth_label"] == bandwidth]
        delays = sorted({row["delay_ms"] for row in subset})
        algorithms = [name for name in ("cubic", "adaptive", "fixed") if any(row["algorithm"] == name for row in subset)]

        for metric, title, ylabel in METRICS:
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            plotted = False
            for algorithm in algorithms:
                xs, ys, errors = [], [], []
                for delay in delays:
                    values = [numeric(row.get(metric)) for row in subset
                              if row["algorithm"] == algorithm and row["delay_ms"] == delay]
                    average, deviation = mean_std(values)
                    if average is not None:
                        xs.append(delay)
                        ys.append(average)
                        errors.append(deviation)
                if xs:
                    ax.errorbar(xs, ys, yerr=errors, marker="o", capsize=4, linewidth=2,
                                label=ALGORITHM_LABELS.get(algorithm, algorithm))
                    plotted = True
            if plotted:
                ax.set_title(f"{title} — Parameters ({scenario}, {bandwidth})")
                ax.set_xlabel("Atraso do enlace de gargalo (ms)")
                ax.set_ylabel(ylabel)
                ax.set_xticks(delays)
                ax.grid(True, alpha=0.3)
                ax.legend()
                save_figure(fig, output_dir, f"{scenario}_{bandwidth}_{metric}")
                generated += 1
            else:
                plt.close(fig)

    return generated


def read_csv(path):
    if not path.is_file():
        print(f"[AVISO] CSV nao encontrado: {path}")
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def plot_heatmap(rows, scenario, metric, title, ylabel, output_dir):
    delays = sorted({numeric(row.get("delay_ms")) for row in rows if numeric(row.get("delay_ms")) is not None})
    algorithms = sorted({row.get("algorithm", "") for row in rows})
    if not delays or not algorithms:
        return False

    matrix = np.full((len(algorithms), len(delays)), np.nan)
    for i, algorithm in enumerate(algorithms):
        for j, delay in enumerate(delays):
            values = [numeric(row.get(metric)) for row in rows
                      if row.get("algorithm") == algorithm and numeric(row.get("delay_ms")) == delay]
            average, _ = mean_std(values)
            if average is not None:
                matrix[i, j] = average

    if np.isnan(matrix).all():
        return False

    fig, ax = plt.subplots(figsize=(8.5, max(4.2, 0.55 * len(algorithms) + 1.5)))
    image = ax.imshow(np.ma.masked_invalid(matrix), aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(delays)))
    ax.set_xticklabels([f"{delay:g}" for delay in delays])
    ax.set_yticks(range(len(algorithms)))
    ax.set_yticklabels([ALGORITHM_LABELS.get(name, name) for name in algorithms])
    ax.set_xlabel("Atraso do enlace de gargalo (ms)")
    ax.set_title(f"{title} — {scenario}")
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label(ylabel)

    finite = matrix[np.isfinite(matrix)]
    midpoint = (float(finite.min()) + float(finite.max())) / 2
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center",
                        color="black" if value > midpoint else "white", fontsize=8)

    safe_scenario = re.sub(r"[^A-Za-z0-9_-]+", "_", scenario)
    save_figure(fig, output_dir, f"{safe_scenario}_{metric}")
    return True


def plot_robustness_campaign(root, output_dir):
    csv_path = root / "consolidated" / "resumo_simulacoes.csv"
    if not csv_path.is_file():
        local_path = PROJECT_DIR / "results" / "robustness_experiments" / "consolidated" / "resumo_simulacoes.csv"
        if local_path.is_file():
            csv_path = local_path
    rows = read_csv(csv_path)
    if not rows:
        print("[AVISO] Nao foi possivel carregar o resumo consolidado de Robustness.")
        return 0

    generated = 0
    for scenario in sorted({row.get("scenario", "cenario") for row in rows}):
        subset = [row for row in rows if row.get("scenario", "cenario") == scenario]
        for metric, title, ylabel in METRICS:
            if plot_heatmap(subset, scenario, metric, title, ylabel, output_dir):
                generated += 1
    write_csv(output_dir / "resumo_robustness.csv", rows)
    print(f"[INFO] CSV utilizado: {csv_path}")
    return generated


def coexistence_metadata(xml_path, root):
    relative_parent = xml_path.relative_to(root).parent
    parts = list(relative_parent.parts)
    if parts and re.fullmatch(r"run[_-]?\\d+", parts[-1], re.IGNORECASE):
        parts = parts[:-1]
    label = "/".join(parts) if parts else "coexistence"
    return {"experiment": label, "repetition": relative_parent.name}


def plot_coexistence_timeseries(root, output_dir):
    generated = 0
    trace_dirs = set()
    for pattern in ("*-cwnd.data", "*-rtt.data"):
        for trace in root.rglob(pattern):
            trace_dirs.add(trace.parent)

    for folder in sorted(trace_dirs):
        for metric, title, ylabel, pattern in (
            ("cwnd", "Evolucao da janela de congestionamento", "CWND (bytes)", "*-cwnd.data"),
            ("rtt", "Evolucao do RTT", "RTT (ms)", "*-rtt.data"),
        ):
            traces = sorted(folder.glob(pattern))
            if not traces:
                continue

            fig, ax = plt.subplots(figsize=(9.0, 5.2))
            plotted = False
            for trace in traces:
                samples = analyze_data_file(str(trace))
                if not samples:
                    continue
                times = [sample[0] for sample in samples]
                values = [sample[1] for sample in samples]
                if metric == "rtt":
                    values = [value * 1000 for value in values]
                flow_match = re.search(r"flow(\\d+)", trace.name, re.IGNORECASE)
                label = f"Fluxo {flow_match.group(1)}" if flow_match else trace.stem
                ax.plot(times, values, linewidth=1.1, label=label)
                plotted = True

            if plotted:
                relative = folder.relative_to(root)
                safe = re.sub(r"[^A-Za-z0-9_-]+", "_", "_".join(relative.parts))
                ax.set_title(f"{title} — {relative}")
                ax.set_xlabel("Tempo (s)")
                ax.set_ylabel(ylabel)
                ax.grid(True, alpha=0.3)
                ax.legend(ncol=2, fontsize=8)
                save_figure(fig, output_dir / "series_temporais", f"{safe}_{metric}")
                generated += 1
            else:
                plt.close(fig)

    return generated


def plot_coexistence_campaign(root, output_dir):
    rows = load_flowmonitor_rows(root, coexistence_metadata)
    generated = 0
    if rows:
        write_csv(output_dir / "resumo_coexistence.csv", rows)
        experiments = sorted({row["experiment"] for row in rows})
        for metric, title, ylabel in METRICS:
            values = []
            labels = []
            errors = []
            for experiment in experiments:
                mean, std = mean_std([numeric(row.get(metric)) for row in rows if row["experiment"] == experiment])
                if mean is not None:
                    labels.append(experiment)
                    values.append(mean)
                    errors.append(std)
            if values:
                fig, ax = plt.subplots(figsize=(max(8.5, 0.7 * len(labels)), 5.2))
                positions = np.arange(len(labels))
                ax.bar(positions, values, yerr=errors, capsize=4)
                ax.set_xticks(positions)
                ax.set_xticklabels(labels, rotation=35, ha="right")
                ax.set_title(f"{title} — Coexistence")
                ax.set_ylabel(ylabel)
                ax.grid(True, axis="y", alpha=0.3)
                save_figure(fig, output_dir, f"coexistence_{metric}")
                generated += 1

    generated += plot_coexistence_timeseries(root, output_dir)
    if generated == 0:
        print("[AVISO] Nenhum XML ou trace CWND/RTT valido encontrado para Coexistence.")
    return generated


def main():
    parser = argparse.ArgumentParser(description="Gera graficos das campanhas TCP.")
    parser.add_argument("--campaign", choices=("all", "parameters", "robustness", "coexistence"), default="all")
    parser.add_argument("--parameters-dir", type=Path, default=PARAMETERS_DIR)
    parser.add_argument("--robustness-dir", type=Path, default=ROBUSTNESS_DIR)
    parser.add_argument("--coexistence-dir", type=Path, default=COEXISTENCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    print(f"Projeto: {PROJECT_DIR}")
    print(f"Saida: {args.output_dir}")
    generated = 0

    if args.campaign in ("all", "parameters"):
        generated += plot_parameter_campaign(args.parameters_dir, args.output_dir / "parameters")
    if args.campaign in ("all", "robustness"):
        generated += plot_robustness_campaign(args.robustness_dir, args.output_dir / "robustness")
    if args.campaign in ("all", "coexistence"):
        generated += plot_coexistence_campaign(args.coexistence_dir, args.output_dir / "coexistence")

    if generated == 0:
        print("\\nNenhum grafico foi gerado. Confira os caminhos e os arquivos de entrada.")
        raise SystemExit(1)
    print(f"\\nConcluido: {generated} grafico(s) em PNG e PDF.")


if __name__ == "__main__":
    main()
