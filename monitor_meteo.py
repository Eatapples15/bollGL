import requests
from datetime import datetime
import json
import os

class SudAlertV17:
    def __init__(self):
        # Filtri zone richiesti
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

    def identify_region(self, row):
        """Innova: Identifica la regione usando province, targhe e parole chiave"""
        nome_z = str(row.get("Nome zona", "")).upper()
        comuni = str(row.get("Comuni", "")).upper()
        
        # 1. Check Prefissi espliciti nel nome zona
        if any(x in nome_z for x in ["CAM", "CAMPANIA"]): return "CAMPANIA"
        if any(x in nome_z for x in ["CAL", "CALABRIA"]): return "CALABRIA"
        if any(x in nome_z for x in ["BAS", "LUCANIA"]): return "BASILICATA"
        
        # 2. Check Geografico nei Comuni (Province e Targhe)
        # CAMPANIA
        if any(x in comuni for x in ["(SA)", "SALERNO", "(NA)", "NAPOLI", "(AV)", "(CE)", "(BN)"]):
            return "CAMPANIA"
        # CALABRIA
        if any(x in comuni for x in ["(CS)", "COSENZA", "(CZ)", "(RC)", "(KR)", "(VV)"]):
            return "CALABRIA"
        # BASILICATA
        if any(x in comuni for x in ["(PZ)", "POTENZA", "(MT)", "MATERA"]):
            return "BASILICATA"
            
        return "UNKNOWN"

    def clean_zone(self, raw_code):
        c = str(raw_code).upper().strip()
        # Rimuove "ZONA ", "CAM-", ecc.
        c = c.replace("ZONA", "").replace("CAM-", "").replace("CAL-", "").replace("BASI-", "").replace("-", "").strip()
        if c.isdigit(): c = str(int(c)) # Rimuove zeri (03 -> 3)
        return c

    def normalize_status(self, val):
        s = str(val).upper().strip()
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
            key = list(data['objects'].keys())[0]
            items = data['objects'][key]['geometries']
            
            for item in items:
                p = item.get("properties", {})
                
                raw_zone = str(p.get("Nome zona", "")).upper()
                raw_crit = str(p.get("Per rischio idrogeologico", "VERDE"))
                
                if not raw_zone or raw_zone == "NONE": continue

                regione = self.identify_region(p)
                clean_z = self.clean_zone(raw_zone)
                crit = self.normalize_status(raw_crit)

                # Matching e Filtraggio
                if regione in self.targets:
                    if clean_z in self.targets[regione]:
                        results[regione.lower()].append({"zona": clean_z, "crit": crit})

        except Exception as e:
            print(f"ERRORE PARSING: {e}")

        # Deduplicazione
        for r in results:
            unique = {z['zona']: z['crit'] for z in results[r]}
            results[r] = [{"zona": k, "crit": v} for k, v in sorted(unique.items())]

        # Metadata
        results["metadata"] = {
            "last_run": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_file": filename
        }

        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        self.save_readme(results, filename)
        print(f"--- FINE: SA:{len(results['campania'])} CS:{len(results['calabria'])} BASI:{len(results['basilicata'])} ---")

    def save_readme(self, results, filename):
        report = f"# 🌩️ Monitoraggio Protezione Civile Sud Italia\n\n"
        report += f"**Bollettino analizzato:** `{filename}`\n"
        report += f"**Ultimo controllo:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        
        emojis = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        
        for r in ["campania", "calabria", "basilicata"]:
            label = f"{r.upper()} (Salerno)" if r == "campania" else f"{r.upper()} (Cosenza)" if r == "calabria" else "BASILICATA"
            report += f"### 📍 {label}\n| Stato | Zona | Criticità |\n|---|---|---|\n"
            if not results[r]:
                report += "| 🟢 | - | Nessuna criticità significativa |\n"
            else:
                for item in results[r]:
                    report += f"| {emojis.get(item['crit'], '⚪')} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)

if __name__ == "__main__":
    SudAlertV17().process()
