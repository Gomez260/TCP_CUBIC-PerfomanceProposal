import csv, os
import consolidate_results as base

PROJECT_DIR = base.PROJECT_DIR
INPUT_DIR = os.path.join(PROJECT_DIR, "results", "robustness_experiments")
OUTPUT_DIR = os.path.join(INPUT_DIR, "consolidated")
SCENARIOS = {
 "bw1_f4": {"bandwidth":"1Mbps","flows":4,"access_delay":"45ms"},
 "bw2_f8": {"bandwidth":"2Mbps","flows":8,"access_delay":"45ms"},
 "access100": {"bandwidth":"2Mbps","flows":4,"access_delay":"100ms"},
}
DELAYS=(10,50,100); RUNS=range(1,6)
CONFIGS=(
 ("Cubic","TcpCubic",None,None),("Bbr","TcpBbr",None,None),
 ("CubicRtt_A0.25_G0.05","TcpCubicRtt",.25,.05),
 ("CubicRtt_A0.10_G0.00","TcpCubicRtt",.10,.00),
 ("CubicRtt_A0.10_G0.025","TcpCubicRtt",.10,.025),
 ("CubicRtt_A0.10_G0.05","TcpCubicRtt",.10,.05),
 ("CubicRtt_A0.10_G0.10","TcpCubicRtt",.10,.10),
 ("CubicRtt_A0.25_G0.00","TcpCubicRtt",.25,.00),
 ("CubicRtt_A0.25_G0.025","TcpCubicRtt",.25,.025),
 ("CubicRtt_A0.50_G0.00","TcpCubicRtt",.50,.00),
 ("CubicRtt_A0.50_G0.025","TcpCubicRtt",.50,.025),
 ("CubicRtt_A0.75_G0.00","TcpCubicRtt",.75,.00),
 ("CubicRtt_A0.75_G0.025","TcpCubicRtt",.75,.025),
 ("CubicRtt_A0.75_G0.05","TcpCubicRtt",.75,.05),
 ("CubicRtt_A0.75_G0.10","TcpCubicRtt",.75,.10),
)

def write_csv(path, rows):
 if rows:
  with open(path,"w",newline="",encoding="utf-8-sig") as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def trace_index(source):
 try:
  p=source.split(".")
  if len(p)==4 and p[:2]==["10","0"] and p[3]=="1":
   i=int(p[2])-1
   return i if 0<=i<=7 else None
 except (AttributeError,ValueError): pass
 return None

def jain(results):
 if not results: return None
 start=min(x["first_rx_ns"] for x in results); end=max(x["last_rx_ns"] for x in results)
 duration=(end-start)/1e9
 if duration<=0: return None
 rates=[x["rx_bytes"]*8/duration for x in results]; total=sum(rates); squares=sum(v*v for v in rates)
 return total*total/(len(rates)*squares) if squares else None

def main():
 os.makedirs(OUTPUT_DIR,exist_ok=True); sims=[]; flows=[]; warnings=[]
 expected=len(SCENARIOS)*len(CONFIGS)*len(DELAYS)*len(RUNS)
 for scenario,info in SCENARIOS.items():
  for label,protocol,alpha,gamma in CONFIGS:
   for delay in DELAYS:
    for run in RUNS:
     folder=os.path.join(INPUT_DIR,scenario,label,f"{delay}ms",f"run_{run}")
     xml=os.path.join(folder,"CubicExperiment.flowmonitor")
     if not os.path.isfile(xml):
      warnings.append(f"FlowMonitor ausente: {xml}"); continue
     try: results=base.analyzer.parse_flowmonitor(xml)
     except Exception as e:
      warnings.append(f"Erro lendo {xml}: {e}"); continue
     if len(results)!=info["flows"]:
      warnings.append(f"{scenario}/{label}/{delay}ms/run_{run}: {len(results)} fluxos; esperado {info['flows']}")
     sims.append({"scenario":scenario,"algorithm":label,"protocol":protocol,"alpha":alpha,"gamma":gamma,
      "bottleneck_bandwidth":info["bandwidth"],"num_flows_expected":info["flows"],"access_delay":info["access_delay"],
      "delay_ms":delay,"repetition":run,**base.calculate_summary(results),"jain_fairness":jain(results)})
     for r in results:
      idx=trace_index(r["source"])
      if idx is None or idx>=info["flows"]:
       warnings.append(f"Origem sem indice de trace: {r['source']} em {xml}"); continue
      m={}
      for metric,scale in (("cwnd",1),("rtt",1000),("inflight",1),("ssth",1)):
       stats,path=base.metric_stats(folder,idx,metric,scale)
       if stats is None: warnings.append(f"Metrica ausente/vazia: {path}"); m[metric]={}
       else: m[metric]=stats
      flows.append({"scenario":scenario,"algorithm":label,"alpha":alpha,"gamma":gamma,"delay_ms":delay,"repetition":run,
       "flowmonitor_id":r["flow"],"tcp_flow_index":idx,"source":r["source"],"destination":r["destination"],
       "tx_bytes":r["tx_bytes"],"rx_bytes":r["rx_bytes"],"tx_packets":r["tx_packets"],"rx_packets":r["rx_packets"],
       "lost_packets":r["lost_packets"],"loss_rate_pct":r["loss_rate"],"throughput_mbps":r["throughput_mbps"],
       "avg_delay_ms":r["avg_delay_ms"],"avg_jitter_ms":r["avg_jitter_ms"],
       "cwnd_min_bytes":m["cwnd"].get("min"),"cwnd_avg_bytes":m["cwnd"].get("avg"),"cwnd_max_bytes":m["cwnd"].get("max"),
       "rtt_min_ms":m["rtt"].get("min"),"rtt_avg_ms":m["rtt"].get("avg"),"rtt_max_ms":m["rtt"].get("max"),
       "inflight_avg_bytes":m["inflight"].get("avg"),"ssth_avg_bytes":m["ssth"].get("avg")})
 write_csv(os.path.join(OUTPUT_DIR,"resumo_simulacoes.csv"),sims)
 write_csv(os.path.join(OUTPUT_DIR,"metricas_fluxos.csv"),flows)
 with open(os.path.join(OUTPUT_DIR,"relatorio_validacao.txt"),"w",encoding="utf-8") as f:
  f.write(f"Simulacoes esperadas: {expected}\nSimulacoes analisadas: {len(sims)}\nFluxos de dados: {len(flows)}\nOcorrencias: {len(warnings)}\n")
  for w in warnings: f.write("- "+w+"\n")
  if not warnings: f.write("Nenhuma ocorrencia estrutural detectada.\n")
 print(f"Simulacoes: {len(sims)}/{expected} | fluxos: {len(flows)} | ocorrencias: {len(warnings)}")
 print(f"Saida: {OUTPUT_DIR}")

if __name__=="__main__": main()
