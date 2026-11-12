#!/usr/bin/env python3
"""Apply the experimental relative-RTT adaptation to the ns-3 submodule.

Run from the main repository root:
    python3 scripts/cubic/apply_relative_rtt_adaptation.py

The script edits only tcp-cubic-rtt.cc/.h inside the ns-3 submodule.
It refuses to run if the expected source fragments are not present.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NS3 = ROOT / "ns3" / "ns-3-dev-git"
CC = NS3 / "src/internet/model/tcp-cubic-rtt.cc"
H = NS3 / "src/internet/model/tcp-cubic-rtt.h"


def replace_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: esperado exatamente 1 trecho, encontrado {count}. Nenhum arquivo foi gravado.")
    return content.replace(old, new, 1)


if not CC.is_file() or not H.is_file():
    raise SystemExit(f"Submodule ns-3 não encontrado em: {NS3}")

cc = CC.read_text(encoding="utf-8")
header = H.read_text(encoding="utf-8")

# Header: declare the smoothed, dimensionless RTT inflation signal.
header = replace_once(
    header,
    "    uint32_t m_sampleCnt;      //!<  Count of samples for HyStart\n    uint32_t m_ackCnt;",
    "    uint32_t m_sampleCnt;      //!<  Count of samples for HyStart\n"
    "    double m_rttIncreaseEwma; //!< Smoothed relative RTT increase over the minimum RTT\n"
    "    uint32_t m_ackCnt;",
    "declaração do estado EWMA no header",
)

# Constructor and copy constructor.
cc = replace_once(
    cc,
    "      m_currRtt(Time::Min()),\n      m_sampleCnt(0)\n",
    "      m_currRtt(Time::Min()),\n      m_sampleCnt(0),\n      m_rttIncreaseEwma(0.0)\n",
    "inicialização do construtor",
)
cc = replace_once(
    cc,
    "      m_currRtt(sock.m_currRtt),\n      m_sampleCnt(sock.m_sampleCnt),\n      m_ackCnt(sock.m_ackCnt),",
    "      m_currRtt(sock.m_currRtt),\n      m_sampleCnt(sock.m_sampleCnt),\n      m_rttIncreaseEwma(sock.m_rttIncreaseEwma),\n      m_ackCnt(sock.m_ackCnt),",
    "cópia do estado EWMA",
)

# C adaptation: retain the existing minimum-RTT/reference adjustment, then
# temper C according to the smoothed relative RTT inflation.
cc = replace_once(
    cc,
    "    return m_c * (1.0 + m_alpha * x);\n}",
    "    const double baseC = m_c * (1.0 + m_alpha * x);\n"
    "    const double inflationFactor = 1.0 + m_alpha * m_rttIncreaseEwma;\n"
    "    return baseC / inflationFactor;\n}",
    "adaptação de C pelo aumento relativo do RTT",
)

# Beta adaptation: a larger relative RTT increase produces a slightly lower
# beta (a stronger multiplicative decrease), bounded by BetaMin/BetaMax.
cc = replace_once(
    cc,
    "    double beta = m_beta + m_gamma * x;\n\n    return std::clamp(beta, m_betaMin, m_betaMax);",
    "    double beta = m_beta + m_gamma * x;\n"
    "    beta -= m_gamma * m_rttIncreaseEwma;\n\n"
    "    return std::clamp(beta, m_betaMin, m_betaMax);",
    "adaptação de Beta pelo aumento relativo do RTT",
)

# Update the signal on each accepted RTT sample. The relative increase is
# clamped to [0, 1] and smoothed with an EWMA (10% new sample, 90% history).
cc = replace_once(
    cc,
    "    if (m_delayMin == Time::Min() || m_delayMin > rtt)\n"
    "    {\n"
    "        m_delayMin = rtt;\n"
    "    }\n\n"
    "    /* hystart triggers when cwnd is larger than some threshold */",
    "    if (m_delayMin == Time::Min() || m_delayMin > rtt)\n"
    "    {\n"
    "        m_delayMin = rtt;\n"
    "    }\n\n"
    "    double relativeIncrease = 0.0;\n"
    "    if (m_delayMin > Time(0))\n"
    "    {\n"
    "        relativeIncrease = std::max(0.0,\n"
    "            (rtt - m_delayMin).GetSeconds() / m_delayMin.GetSeconds());\n"
    "    }\n"
    "    relativeIncrease = std::clamp(relativeIncrease, 0.0, 1.0);\n"
    "    m_rttIncreaseEwma = 0.9 * m_rttIncreaseEwma + 0.1 * relativeIncrease;\n\n"
    "    /* hystart triggers when cwnd is larger than some threshold */",
    "atualização do sinal relativo de RTT em PktsAcked",
)

# A congestion loss starts a fresh measurement epoch.
cc = replace_once(
    cc,
    "    m_delayMin = Time::Min();\n    m_found = false;",
    "    m_delayMin = Time::Min();\n    m_rttIncreaseEwma = 0.0;\n    m_found = false;",
    "reset do sinal relativo após perda",
)

# Add diagnostic visibility to existing debug messages.
cc = replace_once(
    cc,
    '             << " | C adaptive = " << m_cEpoch);',
    '             << " | C adaptive = " << m_cEpoch\n'
    '             << " | RTT relative increase (EWMA) = " << m_rttIncreaseEwma);',
    "log de início de época",
)
cc = replace_once(
    cc,
    '             << " | Beta adaptive = " << beta);',
    '             << " | Beta adaptive = " << beta\n'
    '             << " | RTT relative increase (EWMA) = " << m_rttIncreaseEwma);',
    "log de resposta à perda",
)

# Write only after every expected transformation has passed.
CC.write_text(cc, encoding="utf-8")
H.write_text(header, encoding="utf-8")
print("Alteração experimental aplicada em:")
print(f"  {CC}")
print(f"  {H}")
print("Próximo passo: revisar o diff, compilar e executar um teste curto antes da campanha de 45 simulações.")
