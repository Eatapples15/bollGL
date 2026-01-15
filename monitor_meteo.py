import requests
from datetime import datetime
import json
import os

class SudAlertFinalV15:
    def __init__(self):
        # Filtri richiesti dall'utente
        self.targets = {
            "CAMPANIA": ["3", "5", "6", "7", "8"], # Salerno
            "CALABRIA": ["1", "2"],              # Cosenza
            "BASILICATA": ["A1", "A2", "B", "C", "D", "E1", "E2"]
        }
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def get_data(self):
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    if "tomorrow.json" in fname:
                        print(f"--- ANALISI FILE: {fname} ---")
                        return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"Errore download: {e}")
        return None, None

    def clean_zone(self, raw_code):
        # Converte in stringa e pulisce
        c = str(raw_code).upper().strip()
        # Rimuove i prefissi per il confronto con i filtri
        for p in ["CAM-", "CAL-", "BASI-", "BAS-", "CAM_", "CAL_", "BASI_"]:
            c = c.replace(p, "")
        # Pulisce zeri iniziali (es. 03 -> 3)
        if c.isdigit():
            c = str(int(c))
        return c

    def normalize_status(self, val):
        s = str(val).upper().strip()
        # Mappa i vari modi in cui il DPC scrive il colore
        if any(x in s for x in ["VERDE", "ASSENZA", "1", "0"]): return "VERDE"
        if any(x in s for x in ["GIALLA", "ORDINARIA", "2"]): return "GIALLA"
        if any(x in s for x in ["ARANCIONE", "MODERATA", "3"]): return "ARANCIONE"
        if any(x in s for x in ["ROSSA", "ELEVATA", "4"]): return "ROSSA"
        return "VERDE"

    def process(self):
        data, filename = self.get_data()
        if not data: return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        try:
            # Navigazione TopoJSON
            key = list(data['objects'].keys())[0]
            items = data['objects'][key]['geometries']
            
            for item in items:
                p = item.get("properties", {})
                
                # INNOVAZIONE: Cerchiamo sia nelle chiavi tecniche che in quelle in italiano
                raw_c = str(p.get("Nome zona", p.get("Codice_Area", p.get("codice", "")))).upper()
                raw_crit = str(p.get("Per rischio idrogeologico", p.get("Idro", "VERDE")))
                
                if not raw_c or raw_c == "NONE": continue

                crit = self.normalize_status(raw_crit)
                clean_z = self.clean_zone(raw_c)

                # Identificazione Regione e Match Zone
                if "CAM" in raw_c and clean_z in self.targets["CAMPANIA"]:
                    results["campania"].append({"zona": clean_z, "crit": crit})
                elif "CAL" in raw_c and clean_z in self.targets["CALABRIA"]:
                    results["calabria"].append({"zona": clean_z, "crit": crit})
                elif "BASI" in raw_c or "BAS-" in raw_c:
                    if clean_z in self.targets["BASILICATA"]:
                        results["basilicata"].append({"zona": clean_z, "crit": crit})

        except Exception as e:
            print(f"ERRORE PARSING: {e}")

        # Deduplicazione
        for r in results:
            unique = {z['zona']: z['crit'] for z in results[r]}
            results[r] = [{"zona": k, "crit": v} for k, v in unique.items()]

        # Metadata per forzare il push
        results["metadata"] = {
            "last_run": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_file": filename
        }

        # Salvataggio JSON e README
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        self.save_readme(results, filename)
        print(f"--- FINE: SA:{len(results['campania'])} CS:{len(results['calabria'])} BASI:{len(results['basilicata'])} ---")

    def save_readme(self, results, filename):
        report = f"# 🌩️ Monitoraggio Protezione Civile Sud Italia\n\n"
        report += f"**Bollettino:** `{filename}`\n"
        report += f"**Aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        
        map_emoji = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        
        for r in ["campania", "calabria", "basilicata"]:
            label = r.upper()
            if r == "campania": label += " (Salerno)"
            if r == "calabria": label += " (Cosenza)"
            
            report += f"### 📍 {label}\n| Stato | Zona | Criticità |\n|---|---|---|\n"
            if not results[r]:
                report += "| 🟢 | - | Nessuna criticità significativa |\n"
            else:
                for item in sorted(results[r], key=lambda x: x['zona']):
                    report += f"| {map_emoji.get(item['crit'], '⚪')} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)

if __name__ == "__main__":
    SudAlertFinalV15().process()
