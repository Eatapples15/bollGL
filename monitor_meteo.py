import requests
from datetime import datetime, timedelta
import json
import os

class SudAlertPro:
    def __init__(self):
        # Mappatura Zone (Provincia di Salerno)
        self.salerno_zones = ["3", "5", "6", "7", "8"]
        # Mappatura Zone (Provincia di Cosenza)
        self.cosenza_zones = ["1", "2"]
        # Mappatura Zone (Basilicata)
        self.basilicata_zones = ["A1", "A2", "B", "C", "D", "E1", "E2"]

        # URL Repository Criticità
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def get_latest_json(self):
        """Trova l'ultimo bollettino (Oggi o Tomorrow) tramite API Commits"""
        print(f"[{datetime.now().strftime('%H:%M')}] Ricerca bollettino nei repository DPC...")
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    # Cerchiamo file JSON recenti (2025/2026)
                    if fname.endswith('.json') and ("2025" in fname or "2026" in fname):
                        print(f"✅ File individuato: {fname}")
                        return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"❌ Errore ricerca: {e}")
        return None, None

    def parse_zone_code(self, raw_code):
        """
        Pulisce il codice (es: 'CAM-03' -> '3', 'BASI-A1' -> 'A1')
        Restituisce (regione, codice_pulito)
        """
        code = str(raw_code).upper().strip()
        regione = "UNKNOWN"
        
        if "CAM" in code: regione = "CAMPANIA"
        elif "CAL" in code: regione = "CALABRIA"
        elif "BASI" in code: regione = "BASILICATA"
        
        # Estrae la parte dopo il trattino o prende tutto se manca
        clean_code = code.split("-")[-1] if "-" in code else code
        # Rimuove zeri iniziali per i numeri (es. 03 -> 3)
        if clean_code.isdigit():
            clean_code = str(int(clean_code))
            
        return regione, clean_code

    def get_emoji(self, crit):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(crit).upper(), "⚪")

    def process(self):
        data, filename = self.get_latest_json()
        if not data:
            print("❌ Nessun dato recuperato.")
            return

        # Dizionario finale per data_mappa.json
        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Estrazione dati dalle 'allerte'
        allerte = data.get("allerte", [])
        print(f"Analisi di {len(allerte)} aree nel bollettino...")

        for area in allerte:
            raw_c = area.get("codice", "")
            crit = area.get("criticita_idrogeologica", "VERDE").upper()
            
            reg, code = self.parse_zone_code(raw_c)

            # --- LOGICA FILTRAGGIO SALERNO ---
            if reg == "CAMPANIA" and code in self.salerno_zones:
                results["campania"].append({"zona": code, "crit": crit})
            
            # --- LOGICA FILTRAGGIO COSENZA ---
            elif reg == "CALABRIA" and code in self.cosenza_zones:
                results["calabria"].append({"zona": code, "crit": crit})
            
            # --- LOGICA BASILICATA (TUTTE) ---
            elif reg == "BASILICATA":
                results["basilicata"].append({"zona": code, "crit": crit})

        # --- GENERAZIONE REPORT README ---
        report = f"# 🌩️ Monitoraggio Protezione Civile Sud Italia\n\n"
        report += f"**Bollettino Analizzato:** `{filename}`\n"
        report += f"**Data Elaborazione:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

        for r_name in ["campania", "calabria", "basilicata"]:
            label = r_name.upper()
            if r_name == "campania": label += " (Prov. Salerno)"
            if r_name == "calabria": label += " (Prov. Cosenza)"
            
            report += f"### 📍 {label}\n"
            report += "| Stato | Zona | Criticità |\n|---|---|---|\n"
            
            if not results[r_name]:
                report += "| ⚪ | - | Nessun dato per questa selezione |\n"
            else:
                # Ordina per zona per chiarezza
                sorted_zones = sorted(results[r_name], key=lambda x: x['zona'])
                for item in sorted_zones:
                    report += f"| {self.get_emoji(item['crit'])} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        # --- SALVATAGGIO FILE ---
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)

        print(f"🚀 Fine. Trovati: SA:{len(results['campania'])} | CS:{len(results['calabria'])} | BASI:{len(results['basilicata'])}")

if __name__ == "__main__":
    SudAlertPro().process()
