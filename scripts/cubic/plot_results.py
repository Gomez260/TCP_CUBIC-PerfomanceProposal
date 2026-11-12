#!/usr/bin/env python3
"""
Gera gráficos das campanhas TCP CUBIC/CUBIC-RTT/BBR.

Pré-requisitos:
    pip install matplotlib numpy

Antes de executar, gere os CSVs consolidados com os scripts de análise:
    python3 scripts/cubic/consolidate_results.py
    python3 scripts/cubic/analyze_robustness_experiments.py
    python3 scripts/cubic/analyze_parameter_experiments.py

Uso:
    python3 scripts/cubic/plot_results.py
    python3 scripts/cubic/plot_results.py --campaign initial
    python3 scripts/cubic/plot_results.py --campaign robustness
    python3 scripts/cubic/plot_results.py --campaign parameters

Os arquivos PNG são salvos em results/graficos/.
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
    print(
        "Dependência ausente. Instale com: pip install matplotlib numpy",
        file=sys.stderr,
    )
    raise SystemExit(1) from error


PROJECT_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_DIR / "results"
OUTPUT_DIR = RESULTS_DIR / "graficos"
DELAYS = (10, 50, 100)

INITIAL_METRICS = (
    ("throughput_mbps", "Vazão agregada", "Vazão (Mbps)", "throughput"),
    ("loss_rate_pct", "Taxa de perda", "Perda de pacotes (%)", "packet_loss"),
    ("avg_delay_ms", "Atraso médio", "Atraso (ms)", "delay"),
    ("avg_jitter_ms", "Jitter médio", "Jitter (ms)", "jitter"),
)

FLOW_METRICS = (
    ("cwnd_avg_bytes", "Janela de congestionamento média", "CWND média (bytes)", "cwnd"),
    ("rtt_avg_ms", "RTT médio", "RTT médio (ms)", "rtt"),
)

ROBUSTNESS_METRICS = (
    ("throughput_mbps", "Vazão agregada", "Vazão (Mbps)", "throughput"),
    ("loss_rate_pct", "Taxa de perda", "Perda de pacotes (%)", "packet_loss"),
    ("avg_delay_ms", "Atraso médio", "Atraso (ms)", "delay"),
    ("avg_jitter_ms", "Jitter médio", "Jitter (ms)", "jitter"),
    ("jain_fairness", "Índice de justiça de Jain", "Índice de Jain", "jain_fairness"),
)

PARAMETER_METRICS = ROBUSTNESS_METRICS


def read_csv(path):
    if not path.is_file():
        print(f"[AVISO] CSV não encontrado: {path}")
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def number(value):
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


def save_figure(fig, filename):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / filename
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {destination.relative_to(PROJECT_DIR)}")


def plot_initial():
    summary_path = RESULTS_DIR / "consolidated" / "resumo_simulacoes.csv"
    flow_path = RESULTS_DIR / "consolidated" / "metricas_fluxos.csv"
    simulations = read_csv(summary_path)
    flows = read_csv(flow_path)
    generated = 0

    if simulations:
        algorithms = ("Cubic", "Bbr", "CubicRtt")
        labels = {"Cubic": "CUBIC", "Bbr": "BBR", "CubicRtt": "CUBIC-RTT"}

        for column, title, ylabel, filename in INITIAL_METRICS:
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            has_data = False

            for algorithm in algorithms:
                x_values, y_values, errors = [], [], []
                for delay in DELAYS:
                    values = [
                        number(row.get(column))
                        for row in simulations
                        if row.get("algorithm") == algorithm
                        and number(row.get("delay_ms")) == delay
                    ]
                    average, deviation = mean_std(values)
                    if average is not None:
                        x_values.append(delay)
                        y_values.append(average)
                        errors.append(deviation)

                if x_values:
                    ax.errorbar(
                        x_values, y_values, yerr=errors,
                        marker="o", capsize=4, linewidth=2,
                        label=labels.get(algorithm, algorithm),
                    )
                    has_data = True

            if has_data:
                ax.set_title(f"{title} — campanha inicial")
                ax.set_xlabel("Atraso do enlace de gargalo (ms)")
                ax.set_ylabel(ylabel)
                ax.set_xticks(DELAYS)
                ax.grid(True, alpha=0.3)
                ax.legend()
                save_figure(fig, f"inicial_{filename}.png")
                generated += 1
            else:
                plt.close(fig)

    if flows:
        labels = {"Cubic": "CUBIC", "Bbr": "BBR", "CubicRtt": "CUBIC-RTT"}
        for column, title, ylabel, filename in FLOW_METRICS:
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            has_data = False

            for algorithm in ("Cubic", "Bbr", "CubicRtt"):
                x_values, y_values, errors = [], [], []
                for delay in DELAYS:
                    values = [
                        number(row.get(column))
                        for row in flows
                        if row.get("algorithm") == algorithm
                        and number(row.get("delay_ms")) == delay
                    ]
                    average, deviation = mean_std(values)
                    if average is not None:
                        x_values.append(delay)
                        y_values.append(average)
                        errors.append(deviation)

                if x_values:
                    ax.errorbar(
                        x_values, y_values, yerr=errors,
                        marker="o", capsize=4, linewidth=2,
                        label=labels.get(algorithm, algorithm),
                    )
                    has_data = True

            if has_data:
                ax.set_title(f"{title} — campanha inicial")
                ax.set_xlabel("Atraso do enlace de gargalo (ms)")
                ax.set_ylabel(ylabel)
                ax.set_xticks(DELAYS)
                ax.grid(True, alpha=0.3)
                ax.legend()
                save_figure(fig, f"inicial_{filename}.png")
                generated += 1
            else:
                plt.close(fig)

    return generated


def ordered_configurations(rows):
    names = {row.get("algorithm", "") for row in rows}
    preferred = ["Cubic", "Bbr", "CubicRtt_A0.25_G0.05"]
    return [name for name in preferred if name in names] + sorted(
        name for name in names if name not in preferred
    )


def plot_heatmap(rows, row_key, row_labels, column_key, column_labels,
                 metric, title, colorbar_label, filename, annotate_format=".2f"):
    matrix = np.full((len(row_labels), len(column_labels)), np.nan)
    row_positions = {value: index for index, value in enumerate(row_labels)}
    column_positions = {value: index for index, value in enumerate(column_labels)}
    buckets = defaultdict(list)

    for row in rows:
        row_value = row_key(row)
        column_value = column_key(row)
        value = number(row.get(metric))
        if row_value in row_positions and column_value in column_positions and value is not None:
            buckets[(row_value, column_value)].append(value)

    for (row_value, column_value), values in buckets.items():
        matrix[row_positions[row_value], column_positions[column_value]] = sum(values) / len(values)

    if np.isnan(matrix).all():
        return False

    fig_height = max(4.5, 0.38 * len(row_labels) + 1.8)
    fig, ax = plt.subplots(figsize=(8.5, fig_height))
    masked = np.ma.masked_invalid(matrix)
    image = ax.imshow(masked, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(column_labels)))
    ax.set_xticklabels(column_labels)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_xlabel("Atraso do enlace de gargalo (ms)" if len(column_labels) == 3 else "Gamma")
    ax.set_title(title)

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label(colorbar_label)

    finite = matrix[np.isfinite(matrix)]
    midpoint = (float(finite.min()) + float(finite.max())) / 2
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            if np.isfinite(value):
                text_color = "black" if value > midpoint else "white"
                ax.text(j, i, format(value, annotate_format),
                        ha="center", va="center", color=text_color, fontsize=8)

    save_figure(fig, filename)
    return True


def plot_robustness():
    path = RESULTS_DIR / "robustness_experiments" / "consolidated" / "resumo_simulacoes.csv"
    rows = read_csv(path)
    if not rows:
        return 0

    scenarios = (
        ("bw1_f4", "Gargalo 1 Mbps — 4 fluxos"),
        ("bw2_f8", "Gargalo 2 Mbps — 8 fluxos"),
        ("access100", "Acesso 100 ms — 4 fluxos"),
    )
    configurations = ordered_configurations(rows)
    generated = 0

    for scenario, scenario_title in scenarios:
        scenario_rows = [row for row in rows if row.get("scenario") == scenario]
        if not scenario_rows:
            print(f"[AVISO] Sem dados para o cenário {scenario}.")
            continue

        for column, title, ylabel, filename in ROBUSTNESS_METRICS:
            ok = plot_heatmap(
                scenario_rows,
                row_key=lambda row: row.get("algorithm", ""),
                row_labels=configurations,
                column_key=lambda row: int(number(row.get("delay_ms")) or -1),
                column_labels=list(DELAYS),
                metric=column,
                title=f"{title} — {scenario_title}",
                colorbar_label=ylabel,
                filename=f"robustez_{scenario}_{filename}.png",
            )
            generated += int(ok)

    return generated


def parse_experiment(value):
    match = re.fullmatch(r"A([0-9.]+)_G([0-9.]+)", value or "")
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def plot_parameters():
    path = RESULTS_DIR / "parameter_experiments" / "consolidated" / "resumo_simulacoes.csv"
    rows = read_csv(path)
    if not rows:
        return 0

    parsed = []
    alphas, gammas = set(), set()
    for row in rows:
        parameters = parse_experiment(row.get("experiment"))
        if parameters is None:
            continue
        alpha, gamma = parameters
        alphas.add(alpha)
        gammas.add(gamma)
        parsed.append((row, alpha, gamma))

    if not parsed:
        print("[AVISO] Nenhuma configuração Alpha/Gamma reconhecida no CSV.")
        return 0

    alpha_labels = sorted(alphas)
    gamma_labels = sorted(gammas)
    generated = 0

    for delay in DELAYS:
        delay_rows = [
            (row, alpha, gamma)
            for row, alpha, gamma in parsed
            if number(row.get("delay_ms")) == delay
        ]
        for column, title, ylabel, filename in PARAMETER_METRICS:
            matrix = np.full((len(alpha_labels), len(gamma_labels)), np.nan)
            buckets = defaultdict(list)
            for row, alpha, gamma in delay_rows:
                value = number(row.get(column))
                if value is not None:
                    buckets[(alpha, gamma)].append(value)

            for (alpha, gamma), values in buckets.items():
                matrix[alpha_labels.index(alpha), gamma_labels.index(gamma)] = (
                    sum(values) / len(values)
                )

            if np.isnan(matrix).all():
                continue

            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            image = ax.imshow(np.ma.masked_invalid(matrix), aspect="auto", cmap="viridis")
            ax.set_xticks(range(len(gamma_labels)))
            ax.set_xticklabels([f"{value:g}" for value in gamma_labels])
            ax.set_yticks(range(len(alpha_labels)))
            ax.set_yticklabels([f"{value:g}" for value in alpha_labels])
            ax.set_xlabel("Gamma")
            ax.set_ylabel("Alpha")
            ax.set_title(f"{title} — experimentos de parâmetros — {delay} ms")
            colorbar = fig.colorbar(image, ax=ax)
            colorbar.set_label(ylabel)

            finite = matrix[np.isfinite(matrix)]
            midpoint = (float(finite.min()) + float(finite.max())) / 2
            for i in range(matrix.shape[0]):
                for j in range(matrix.shape[1]):
                    value = matrix[i, j]
                    if np.isfinite(value):
                        text_color = "black" if value > midpoint else "white"
                        ax.text(j, i, f"{value:.2f}", ha="center", va="center",
                                color=text_color, fontsize=8)

            save_figure(fig, f"parametros_{delay}ms_{filename}.png")
            generated += 1

    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Gera gráficos das campanhas de simulação TCP."
    )
    parser.add_argument(
        "--campaign",
        choices=("all", "initial", "robustness", "parameters"),
        default="all",
        help="Campanha a ser representada (padrão: all).",
    )
    args = parser.parse_args()

    print(f"Projeto: {PROJECT_DIR}")
    print(f"Destino dos gráficos: {OUTPUT_DIR}")
    generated = 0

    if args.campaign in ("all", "initial"):
        generated += plot_initial()
    if args.campaign in ("all", "robustness"):
        generated += plot_robustness()
    if args.campaign in ("all", "parameters"):
        generated += plot_parameters()

    if generated == 0:
        print(
            "\nNenhum gráfico foi gerado. Verifique se os CSVs consolidados "
            "existem e possuem dados."
        )
        print("Consulte o cabeçalho do script para os comandos de consolidação.")
        raise SystemExit(1)

    print(f"\nConcluído: {generated} gráfico(s) salvo(s) em {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
