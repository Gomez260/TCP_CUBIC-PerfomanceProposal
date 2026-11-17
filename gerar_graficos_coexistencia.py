
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

CSV_FILE = "resultados_8flows.csv"
OUTPUT_DIR = Path("graficos_coexistencia")

OUTPUT_DIR.mkdir(exist_ok=True)

DELAYS = ["10ms", "50ms", "100ms"]

# ==========================================================
# LEITURA DOS RESULTADOS
# ==========================================================

df = pd.read_csv(CSV_FILE)

required_columns = [
    "delay",
    "run",
    "source",
    "tx_packets",
    "lost_packets",
    "throughput_mbps",
    "mean_delay_ms",
    "mean_jitter_ms"
]

missing = [col for col in required_columns if col not in df.columns]

if missing:
    raise ValueError(f"Colunas ausentes no CSV: {missing}")

# ==========================================================
# IDENTIFICAÇÃO DOS ALGORITMOS
# ==========================================================

# Os endereços de origem identificam os oito fluxos.
# Fluxos ímpares: CUBIC
# Fluxos pares: CUBIC-RTT

df["flow_number"] = (
    df["source"]
    .str.extract(r"10\.0\.(\d+)\.1$")[0]
    .astype(int)
)

df["algorithm"] = df["flow_number"].apply(
    lambda x: "CUBIC" if x % 2 != 0 else "CUBIC-RTT"
)

# ==========================================================
# AGREGAÇÃO POR EXECUÇÃO
# ==========================================================

# Primeiro agrupamos os quatro fluxos de cada algoritmo
# dentro de cada execução experimental.
#
# Depois calculamos a média e o desvio entre as cinco
# repetições de cada cenário.

run_results = (
    df.groupby(["delay", "run", "algorithm"])
    .agg(
        throughput_mbps=("throughput_mbps", "mean"),
        mean_delay_ms=("mean_delay_ms", "mean"),
        mean_jitter_ms=("mean_jitter_ms", "mean"),
        tx_packets=("tx_packets", "sum"),
        lost_packets=("lost_packets", "sum")
    )
    .reset_index()
)

run_results["loss_percent"] = (
    run_results["lost_packets"]
    / run_results["tx_packets"]
    * 100
)

# ==========================================================
# VALIDAÇÃO DOS DADOS
# ==========================================================

print("\n========== VALIDAÇÃO ==========")

print(f"Total de registros: {len(df)}")
print(f"Total de execuções: {df.groupby(['delay', 'run']).ngroups}")

for delay in DELAYS:
    subset = df[df["delay"] == delay]

    print(f"\nCenário {delay}")
    print(f"Registros: {len(subset)}")

    for algorithm in ["CUBIC", "CUBIC-RTT"]:
        count = subset[
            subset["algorithm"] == algorithm
        ].groupby("run").size()

        print(f"{algorithm}: {count.to_dict()}")

# ==========================================================
# FUNÇÃO PARA GERAR GRÁFICOS
# ==========================================================

def generate_plot(metric, title, ylabel, filename):

    plt.figure(figsize=(9, 5.5))

    for algorithm in ["CUBIC", "CUBIC-RTT"]:

        means = []
        stds = []

        for delay in DELAYS:

            values = run_results[
                (run_results["delay"] == delay) &
                (run_results["algorithm"] == algorithm)
            ][metric]

            means.append(values.mean())
            stds.append(values.std())

        plt.errorbar(
            DELAYS,
            means,
            yerr=stds,
            marker="o",
            markersize=7,
            linewidth=2,
            capsize=5,
            label=algorithm
        )

    plt.title(title, fontsize=13)
    plt.xlabel("Atraso configurado no gargalo (ms)")
    plt.ylabel(ylabel)

    plt.grid(
        True,
        linestyle="--",
        alpha=0.4
    )

    plt.legend(title="Algoritmo TCP")

    plt.tight_layout()

    output_path = OUTPUT_DIR / filename

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(f"Gráfico gerado: {output_path}")


# ==========================================================
# GRÁFICO 1 - THROUGHPUT
# ==========================================================

generate_plot(
    metric="throughput_mbps",
    title="Comparação de Throughput - CUBIC vs CUBIC-RTT",
    ylabel="Throughput médio por fluxo (Mbps)",
    filename="01_throughput.png"
)


# ==========================================================
# GRÁFICO 2 - ATRASO MÉDIO
# ==========================================================

generate_plot(
    metric="mean_delay_ms",
    title="Comparação de Atraso Médio",
    ylabel="Atraso médio (ms)",
    filename="02_atraso_medio.png"
)


# ==========================================================
# GRÁFICO 3 - JITTER
# ==========================================================

generate_plot(
    metric="mean_jitter_ms",
    title="Comparação de Jitter",
    ylabel="Jitter médio (ms)",
    filename="03_jitter.png"
)


# ==========================================================
# GRÁFICO 4 - PACKET LOSS
# ==========================================================

generate_plot(
    metric="loss_percent",
    title="Comparação de Perda de Pacotes",
    ylabel="Perda de pacotes (%)",
    filename="04_packet_loss.png"
)


# ==========================================================
# EXPORTAÇÃO DA TABELA ESTATÍSTICA
# ==========================================================

summary = (
    run_results
    .groupby(["delay", "algorithm"])[
        [
            "throughput_mbps",
            "mean_delay_ms",
            "mean_jitter_ms",
            "loss_percent"
        ]
    ]
    .agg(["mean", "std"])
    .round(4)
)

summary.to_csv(
    OUTPUT_DIR / "resumo_estatistico.csv"
)

print("\n===================================")
print("ANÁLISE CONCLUÍDA!")
print(f"Resultados salvos em: {OUTPUT_DIR}")
print("===================================")
