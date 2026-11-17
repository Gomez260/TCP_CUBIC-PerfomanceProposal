
import xml.etree.ElementTree as ET
import csv
import argparse
from pathlib import Path
from collections import defaultdict

def analyze_file(file_path, scenario, delay, run):
    tree = ET.parse(file_path)
    root = tree.getroot()

    classifier = root.find("Ipv4FlowClassifier")
    flow_stats = root.find("FlowStats")

    if classifier is None or flow_stats is None:
        raise ValueError(f"XML inválido: {file_path}")

    flows = {}

    for flow in classifier.findall("Flow"):
        flow_id = int(flow.get("flowId"))

        flows[flow_id] = {
            "source": flow.get("sourceAddress"),
            "destination": flow.get("destinationAddress"),
            "protocol": flow.get("protocol"),
            "source_port": flow.get("sourcePort"),
            "destination_port": flow.get("destinationPort")
        }

    results = []

    for flow in flow_stats.findall("Flow"):
        flow_id = int(flow.get("flowId"))

        if flow_id not in flows:
            continue

        info = flows[flow_id]

        # Fluxos de aplicação: porta de origem efêmera
        # e porta de destino 50000.
        if int(info["destination_port"]) != 50000:
            continue

        tx_bytes = int(flow.get("txBytes", 0))
        rx_bytes = int(flow.get("rxBytes", 0))
        tx_packets = int(flow.get("txPackets", 0))
        rx_packets = int(flow.get("rxPackets", 0))
        lost_packets = int(flow.get("lostPackets", 0))

        delay_sum = float(
            flow.get("delaySum", "0").replace("ns", "")
        )

        jitter_sum = float(
            flow.get("jitterSum", "0").replace("ns", "")
        )

        # FlowMonitor registra tempos em nanosegundos.
        delay_seconds = delay_sum / 1e9
        jitter_seconds = jitter_sum / 1e9

        mean_delay_ms = (
            delay_seconds / rx_packets * 1000
            if rx_packets > 0 else 0
        )

        mean_jitter_ms = (
            jitter_seconds / (rx_packets - 1) * 1000
            if rx_packets > 1 else 0
        )

        # Janela de medição configurada na simulação.
        # O usuário deve informar a duração efetiva.
        results.append({
            "scenario": scenario,
            "delay": delay,
            "run": run,
            "flow_id": flow_id,
            "source": info["source"],
            "destination": info["destination"],
            "tx_bytes": tx_bytes,
            "rx_bytes": rx_bytes,
            "tx_packets": tx_packets,
            "rx_packets": rx_packets,
            "lost_packets": lost_packets,
            "throughput_mbps": rx_bytes * 8 / 1_000_000,
            "mean_delay_ms": mean_delay_ms,
            "mean_jitter_ms": mean_jitter_ms,
            "loss_percent": (
                lost_packets / tx_packets * 100
                if tx_packets > 0 else 0
            )
        })

    return results


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--root",
        required=True,
        help="Diretório raiz dos resultados"
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=300.0,
        help="Duração da janela de medição em segundos"
    )

    parser.add_argument(
        "--output",
        default="flowmonitor_results.csv"
    )

    args = parser.parse_args()

    root = Path(args.root)
    all_results = []

    files = sorted(root.rglob("*.flowmonitor"))

    if not files:
        print("Nenhum arquivo FlowMonitor encontrado.")
        return

    for file in files:
        run_dir = file.parent.name
        delay = file.parent.parent.name
        scenario = file.parent.parent.parent.name

        try:
            run = int(run_dir.replace("run_", ""))
        except ValueError:
            print(f"Run não identificado: {file}")
            continue

        print(f"Analisando: {scenario}/{delay}/{run_dir}")

        results = analyze_file(
            file,
            scenario,
            delay,
            run
        )

        for result in results:
            result["duration_seconds"] = args.duration

            result["throughput_mbps"] /= args.duration

        all_results.extend(results)

    if not all_results:
        print("Nenhum fluxo de aplicação identificado.")
        return

    output = Path(args.output)

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=all_results[0].keys()
        )

        writer.writeheader()
        writer.writerows(all_results)

    print("\n====================================")
    print("ANÁLISE CONCLUÍDA")
    print("====================================")
    print(f"Arquivos analisados: {len(files)}")
    print(f"Fluxos identificados: {len(all_results)}")
    print(f"Resultado: {output.resolve()}")


if __name__ == "__main__":
    main()
