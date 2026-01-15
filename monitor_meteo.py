import requests
from datetime import datetime
import json
import os
import time

class SudAlertOfficialMapping:
    def __init__(self):
        # MAPPATURA UFFICIALE DPC 2026
        self.mapping = {
            "CAMPANIA": {
                "3": "PENISOLA SORRENTINO-AMALFITANA, MONTI DI SARNO E MONTI PICENTINI",
                "5": "TUSCIANO E ALTO SELE",
                "6": "PIANA SELE E ALTO CILENTO",
                "7": "TANAGRO",
                "8": "BASSO CILENTO"
            },
            "CALABRIA": {
                "1": "VERSANTE TIRRENICO SETTENTRIONALE",
                "2": "VERSANTE TIRRENICO CENTRO-SETTENTRIONALE"
            }
        }
        # La Basilicata usa prefissi standard (BASI-A1, BASI-B, etc.)
        self.basilicata_targets = ["A1", "A2", "B", "C", "D", "E1", "E2"]
        
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def fetch_data(self):
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    if "tomorrow.json" in fname and "202" in fname:
                        print(f"--- ANALISI FILE: {fname} ---")
                        return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"Errore: {e}")
        return None, None

    def get_color(self, props):
        # Cerchiamo la criticità idrogeologica (colore mappa)
        txt = str(props.get("Rappresentata nella mappa", props.get("Per rischio idrogeologico", "VERDE"))).upper()
        if "ROSSA" in txt or "ELEVATA" in txt: return "ROSSA"
        if "ARANCIONE" in txt or "MODERATA" in txt: return "ARANCIONE"
        if "GIALLA" in txt or "ORDINARIA" in txt: return "GIALLA"
        return "VERDE"

    def process(self):
        data, fname = self.fetch_data()
        if not data: return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Accesso Geometrie TopoJSON
        obj_key = list(data['objects'].keys())[0]
        geometries = data['objects'][obj_key]['geometries']

        for geo in geometries:
            p = geo.get("properties", {})
            raw_name = str(p.get("Nome zona", "")).upper().strip()
            color = self.get_color(p)

            # 1. MATCH CAMPANIA (SALERNO)
            for code, official_name in self.mapping["CAMPANIA"].items():
                if official_name in raw_name:
                    results["campania"].append({"zona": code, "crit": color})

            # 2. MATCH CALABRIA (COSENZA)
            for code, official_name in self.mapping["CALABRIA"].items():
                if official_name in raw_name:
                    results["calabria"].append({"zona": code, "crit": color})

            # 3. MATCH BASILICATA
            if "BASI-" in raw_name:
                clean_b = raw_name.replace("BASI-", "").strip()
                if clean_b in self.basilicata_targets:
                    results["basilicata"].append({"zona": clean_b, "crit": color})

        # Deduplicazione e pulizia
        for r in ["campania", "calabria", "basilicata"]:
            # Usiamo un dizionario per tenere solo l'ultima occorrenza (o la più grave)
            unique = {}
            for item in results[r]:
                unique[item['zona']] = item['crit']
            results[r] = [{"zona": k, "crit": v} for k, v in sorted(unique.items())]

        # Force Update per GitHub
        results["metadata"] = {
            "timestamp": time.time_ns(),
            "last_update": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            "file_source": fname
        }

        # Salvataggio File
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        self.write_readme(results)
        print(f"✅ SA:{len(results['campania'])} | CS:{len(results['calabria'])} | BASI:{len(results['basilicata'])}")

    def write_readme(self, results):
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        report = f"# 🌩️ Monitoraggio Sud Italia\n\n"
        report += f"**Ultimo Aggiornamento:** {now}\n"
        report += f"**File Analizzato:** `{results['metadata']['file_source']}`\n\n"
        
        emoji = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        
        for r in ["campania", "calabria", "basilicata"]:
            title = r.upper()
            if r == "campania": title += " (Salerno)"
            elif r == "calabria": title += " (Cosenza)"
            
            report += f"### 📍 {title}\n| Stato | Zona | Allerta |\n|---|---|---|\n"
            if not results[r]:
                report += "| ⚪ | - | Nessun dato trovato |\n"
            else:
                for item in results[r]:
                    report += f"| {emoji.get(item['crit'], '⚪')} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)

if __name__ == "__main__":
    SudAlertOfficialMapping().process()
