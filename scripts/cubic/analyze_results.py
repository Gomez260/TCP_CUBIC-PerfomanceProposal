import os
import sys
import xml.etree.ElementTree as ET


def parse_time_ns(value):
    return float(
        value.replace("+", "")
             .replace("ns", "")
    )


def parse_flowmonitor(filename):

    tree = ET.parse(filename)
    root = tree.getroot()

    classifier = root.find(".//Ipv4FlowClassifier")

    forward_flows = {}

    if classifier is not None:
        for flow in classifier.findall("Flow"):

            flow_id = flow.attrib["flowId"]
            source = flow.attrib["sourceAddress"]
            destination = flow.attrib["destinationAddress"]

            source_port = flow.attrib["sourcePort"]
            destination_port = flow.attrib["destinationPort"]

            if destination_port == "50000":
                forward_flows[flow_id] = {
                    "source": source,
                    "destination": destination,
                    "source_port": source_port,
                    "destination_port": destination_port
                }

    flow_stats = root.find(".//FlowStats")

    results = []

    if flow_stats is not None:

        for flow in flow_stats.findall("Flow"):

            flow_id = flow.attrib["flowId"]

            if flow_id not in forward_flows:
                continue

            tx_bytes = int(flow.attrib.get("txBytes", 0))
            rx_bytes = int(flow.attrib.get("rxBytes", 0))

            tx_packets = int(flow.attrib.get("txPackets", 0))
            rx_packets = int(flow.attrib.get("rxPackets", 0))
            lost_packets = int(flow.attrib.get("lostPackets", 0))

            if tx_bytes == 0 and rx_bytes == 0:
                continue

            delay_ns = parse_time_ns(
                flow.attrib.get("delaySum", "+0ns")
            )

            jitter_ns = parse_time_ns(
                flow.attrib.get("jitterSum", "+0ns")
            )

            first_rx_ns = parse_time_ns(
                flow.attrib.get("timeFirstRxPacket", "+0ns")
            )

            last_rx_ns = parse_time_ns(
                flow.attrib.get("timeLastRxPacket", "+0ns")
            )

            avg_delay_ms = 0
            avg_jitter_ms = 0
            loss_rate = 0
            throughput_mbps = 0

            if rx_packets > 0:

                avg_delay_ms = (
                    delay_ns / rx_packets
                ) / 1e6

                avg_jitter_ms = (
                    jitter_ns / rx_packets
                ) / 1e6

            if tx_packets > 0:

                loss_rate = (
                    lost_packets / tx_packets
                ) * 100

            duration_ns = last_rx_ns - first_rx_ns

            if duration_ns > 0:

                duration_seconds = duration_ns / 1e9

                throughput_bps = (
                    rx_bytes * 8
                ) / duration_seconds

                throughput_mbps = (
                    throughput_bps / 1e6
                )

            info = forward_flows[flow_id]

            results.append({
                "flow": flow_id,
                "source": info["source"],
                "destination": info["destination"],
                "tx_bytes": tx_bytes,
                "rx_bytes": rx_bytes,
                "tx_packets": tx_packets,
                "rx_packets": rx_packets,
                "lost_packets": lost_packets,
                "loss_rate": loss_rate,
                "throughput_mbps": throughput_mbps,
                "avg_delay_ms": avg_delay_ms,
                "avg_jitter_ms": avg_jitter_ms
            })

    return results


def print_results(results):

    print("\n==========================================")
    print("       TCP CUBIC - RESULTADOS")
    print("==========================================\n")

    total_tx = 0
    total_rx = 0
    total_lost = 0

    total_delay = 0
    total_jitter = 0

    for result in results:

        print(f"Flow {result['flow']}")
        print(f"  Origem:         {result['source']}")
        print(f"  Destino:        {result['destination']}")
        print(f"  TX Bytes:       {result['tx_bytes']}")
        print(f"  RX Bytes:       {result['rx_bytes']}")
        print(f"  TX Packets:     {result['tx_packets']}")
        print(f"  RX Packets:     {result['rx_packets']}")
        print(f"  Lost Packets:   {result['lost_packets']}")
        print(f"  Loss Rate:      {result['loss_rate']:.2f}%")
        print(f"  Throughput:     {result['throughput_mbps']:.2f} Mbps")
        print(f"  Avg Delay:      {result['avg_delay_ms']:.2f} ms")
        print(f"  Avg Jitter:     {result['avg_jitter_ms']:.2f} ms")
        print()

        total_tx += result["tx_bytes"]
        total_rx += result["rx_bytes"]
        total_lost += result["lost_packets"]

        total_delay += result["avg_delay_ms"]
        total_jitter += result["avg_jitter_ms"]

    print("==========================================")
    print("          RESUMO DO CENÁRIO")
    print("==========================================")

    print(f"Fluxos CUBIC:       {len(results)}")
    print(f"TX total:           {total_tx} bytes")
    print(f"RX total:           {total_rx} bytes")
    print(f"Pacotes perdidos:   {total_lost}")

    if results:

        total_throughput = sum(
            r["throughput_mbps"]
            for r in results
        )

        avg_loss = sum(
            r["loss_rate"]
            for r in results
        ) / len(results)

        avg_delay = total_delay / len(results)
        avg_jitter = total_jitter / len(results)

        print(
            f"Throughput agregado: {total_throughput:.2f} Mbps"
        )

        print(
            f"Perda média:         {avg_loss:.2f}%"
        )

        print(
            f"Atraso médio:        {avg_delay:.2f} ms"
        )

        print(
            f"Jitter médio:        {avg_jitter:.2f} ms"
        )

    print()


def analyze_data_file(filename):

    values = []

    if not os.path.exists(filename):
        return values

    with open(filename, "r") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 2:
                continue

            try:

                time = float(parts[0])
                value = float(parts[1])

                values.append((time, value))

            except ValueError:
                continue

    return values


def print_tcp_metrics(scenario):

    project_dir = os.path.expanduser(
        "~/TCP_CUBIC-PerfomanceProposal"
    )

    results_dir = os.path.join(
        project_dir,
        "results",
        "cubic",
        scenario
    )

    print("\n==========================================")
    print("       MÉTRICAS TCP CUBIC")
    print("==========================================\n")

    for flow in range(4):

        cwnd_file = os.path.join(
            results_dir,
            f"CubicExperiment-flow{flow}-cwnd.data"
        )

        rtt_file = os.path.join(
            results_dir,
            f"CubicExperiment-flow{flow}-rtt.data"
        )

        cwnd = analyze_data_file(cwnd_file)
        rtt = analyze_data_file(rtt_file)

        print(f"Flow {flow}")

        if cwnd:

            cwnd_values = [
                value for _, value in cwnd
                if value > 0
            ]

            print(
                f"  CWND mínimo:   {min(cwnd_values):.2f}"
            )

            print(
                f"  CWND máximo:   {max(cwnd_values):.2f}"
            )

            print(
                f"  CWND médio:    "
                f"{sum(cwnd_values) / len(cwnd_values):.2f}"
            )

        else:

            print("  CWND: sem dados")

        if rtt:

            rtt_values = [
                value for _, value in rtt
                if value > 0
            ]

            print(
                f"  RTT mínimo:    "
                f"{min(rtt_values) * 1000:.2f} ms"
            )

            print(
                f"  RTT máximo:    "
                f"{max(rtt_values) * 1000:.2f} ms"
            )

            print(
                f"  RTT médio:     "
                f"{sum(rtt_values) / len(rtt_values) * 1000:.2f} ms"
            )

        else:

            print("  RTT: sem dados")

        print()


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print("Uso:")
        print(
            "python3 scripts/cubic/analyze_results.py <cenario>"
        )

        sys.exit(1)

    scenario = sys.argv[1]

    project_dir = os.path.expanduser(
        "~/TCP_CUBIC-PerfomanceProposal"
    )

    flowmonitor = os.path.join(
        project_dir,
        "results",
        "cubic",
        scenario,
        "CubicExperiment.flowmonitor"
    )

    if not os.path.exists(flowmonitor):

        print("Arquivo não encontrado:")
        print(flowmonitor)

        sys.exit(1)

    results = parse_flowmonitor(flowmonitor)

    print_results(results)

    print_tcp_metrics(scenario)