import requests
from datetime import datetime, timedelta
import json
import os

class SouthAlertHubFinal:
    def __init__(self):
        # CONFIGURAZIONE ZONE RICHIESTE
        # Campania: Solo Salerno
        self.target_campania = ["3", "5", "6", "7", "8"]
        # Calabria: Solo Cosenza (Zone 1 e 2)
        self.target_calabria = ["1", "2"]
        # Basilicata: Tutte le zone
        self.target_basilicata = ["A1", "A2", "B", "C", "D", "E1", "E2"]

        # Parametri Repository
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"
        self.base_raw_url = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/"

    def get_latest_data(self):
        """Trova l'ultimo bollettino disponibile tramite Git Commits o Date-Guessing"""
        print(f"[{datetime.now().strftime('%H:%M')}] Avvio ricerca bollettino...")
        
        # 1. Tentativo tramite API Commits (per file recenti su master/main)
        try:
            res = requests.get(self.repo_api, timeout=10)
            if res.status_code == 200:
                commits = res.json()
                for commit in commits:
                    detail = requests.get(commit['url']).json()
                    for f in detail.get('files', []):
                        fname = f['filename'].split('/')[-1]
                        if fname.endswith('.json') and fname.startswith('202'):
                            print(f"✅ Bollettino trovato: {fname}")
                            return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"⚠️ Errore API: {e}")

        # 2. Fallback Predittivo (Oggi/Ieri)
        for d in [0, 1]:
            date_str = (datetime.now() - timedelta(days=d)).strftime("%Y%m%d")
            for hhmm in ["1430", "1500", "1530", "1600"]:
                url = f"{self.base_raw_url}{date_str}_{hhmm}.json"
                r = requests.get(url)
                if r.status_code == 200:
                    print(f"✅ Bollettino trovato (Predictive): {date_str}_{hhmm}.json")
                    return r.json(), f"{date_str}_{hhmm}.json"
        
        return None, None

    def normalize_code(self, raw_code):
        """Converte CAM-03 in 3, BASI-A1 in A1, etc."""
        if "-" in raw_code:
            code = raw_code.split("-")[1]
            # Rimuove lo zero iniziale se presente (es. 03 -> 3) ma non da A1
            if code.isdigit():
                return str(int(code))
            return code.upper()
        return raw_code.upper()

    def get_emoji(self, crit):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(crit).upper(), "⚪")

    def process(self):
        data, filename = self.get_latest_data()
        if not data:
            print("❌ Impossibile recuperare i dati.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Estrazione e filtraggio
        for area in data.get("allerte", []):
            raw_code = str(area.get("codice", "")).upper()
            crit = area.get("criticita_idrogeologica", "VERDE").upper()
            clean_z = self.normalize_code(raw_code)

            # Match CAMPANIA (Salerno)
            if "CAM-" in raw_code and clean_z in self.target_campania:
                results["campania"].append({"zona": clean_z, "crit": crit})
            
            # Match CALABRIA (Cosenza)
            elif "CAL-" in raw_code and clean_z in self.target_calabria:
                results["calabria"].append({"zona": clean_z, "crit": crit})
            
            # Match BASILICATA (Tutte)
            elif "BASI-" in raw_code:
                results["basilicata"].append({"zona": clean_z, "crit": crit})

        # Generazione README Dashboard
        report = f"# 🌩️ Dashboard Monitoraggio Sud Italia\n\n"
        report += f"**Aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        report += f"**Sorgente:** `{filename}`\n\n"

        for reg in ["campania", "calabria", "basilicata"]:
            label = "CAMPANIA (Salerno)" if reg == "campania" else "CALABRIA (Cosenza)" if reg == "calabria" else "BASILICATA"
            report += f"### 📍 {label}\n"
            report += "| Stato | Zona | Criticità |\n|---|---|---|\n"
            if not results[reg]:
                report += "| ⚪ | - | Nessun dato trovato |\n"
            else:
                for item in sorted(results[reg], key=lambda x: x['zona']):
                    report += f"| {self.get_emoji(item['crit'])} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        # Scrittura File
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        print(f"🚀 Successo! Campania: {len(results['campania'])}, Calabria: {len(results['calabria'])}, Basilicata: {len(results['basilicata'])}")

if __name__ == "__main__":
    SouthAlertHubFinal().process()
