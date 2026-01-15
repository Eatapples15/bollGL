import requests
from datetime import datetime
import json
import os

class SudAlertV14:
    def __init__(self):
        # Zone obiettivo richieste
        self.targets = {
            "CAMPANIA": ["3", "5", "6", "7", "8"],
            "CALABRIA": ["1", "2"],
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
                    # Cerchiamo il bollettino di domani (previsionale)
                    if "tomorrow.json" in fname:
                        print(f"--- ANALISI FILE: {fname} ---")
                        return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"Errore download: {e}")
        return None, None

    def clean_zone(self, raw_code):
        c = str(raw_code).upper().strip()
        # Rimuove prefissi comuni usati dal DPC
        for p in ["CAM-", "CAL-", "BASI-", "BAS-", "CAM_", "CAL_", "BASI_"]:
            c = c.replace(p, "")
        # Se rimane un numero con lo zero (es. 03), lo pulisce in '3'
        if c.isdigit():
            c = str(int(c))
        return c

    def process(self):
        data, filename = self.get_data()
        if not data:
            print("Nessun dato recuperato dal repository.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        all_raw_codes = []

        try:
            # Navigazione TopoJSON: objects -> bollettino -> geometries
            key = list(data['objects'].keys())[0]
            items = data['objects'][key]['geometries']
            
            # Debug: vediamo quali campi esistono nel primo oggetto
            if items:
                print(f"DEBUG - Campi disponibili: {list(items[0].get('properties', {}).keys())}")

            for item in items:
                p = item.get("properties", {})
                
                # Cerchiamo il codice in tutte le chiavi possibili
                raw_c = str(p.get("Codice_Area", p.get("codice", p.get("Codice", "")))).upper()
                if raw_c:
                    all_raw_codes.append(raw_c)
                
                # Normalizzazione Criticità (Idrogeologica)
                crit = str(p.get("Idro", p.get("Idrogeologica", "VERDE"))).upper()
                if crit in ["1", "VERDE", "0", "NULL"]: crit = "VERDE"
                elif crit in ["2", "GIALLA"]: crit = "GIALLA"
                elif crit in ["3", "ARANCIONE"]: crit = "ARANCIONE"
                elif crit in ["4", "ROSSA"]: crit = "ROSSA"

                clean_z = self.clean_zone(raw_c)

                # Matching per Regione
                if "CAM" in raw_c and clean_z in self.targets["CAMPANIA"]:
                    results["campania"].append({"zona": clean_z, "crit": crit})
                elif "CAL" in raw_c and clean_z in self.targets["CALABRIA"]:
                    results["calabria"].append({"zona": clean_z, "crit": crit})
                elif "BASI" in raw_c or "BAS-" in raw_c: # Corretto raw_code in raw_c
                    if clean_z in self.targets["BASILICATA"]:
                        results["basilicata"].append({"zona": clean_z, "crit": crit})

        except Exception as e:
            print(f"ERRORE DURANTE IL PARSING: {e}")

        # Log per capire se i codici sono diversi dal previsto
        if all_raw_codes:
            print(f"DEBUG - Esempi codici trovati: {all_raw_codes[:5]}")
        else:
            print("ATTENZIONE: Nessun codice trovato nelle proprietà degli oggetti.")

        # Deduplicazione (le zone possono avere più poligoni)
        for r in ["campania", "calabria", "basilicata"]:
            unique = {z['zona']: z['crit'] for z in results[r]}
            results[r] = [{"zona": k, "crit": v} for k, v in unique.items()]

        # Metadati per forzare il push su GitHub (cambiano ogni volta)
        results["metadata"] = {
            "last_run": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_file": filename
        }

        # Salvataggio file
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        # Generazione README
        self.save_readme(results, filename)

    def save_readme(self, results, filename):
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        report = f"# 🌩️ Monitoraggio Protezione Civile Sud Italia\n\n"
        report += f"**Bollettino analizzato:** `{filename}`\n"
        report += f"**Ultimo controllo:** {now_str}\n\n"
        
        emoji_map = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}

        for r in ["campania", "calabria", "basilicata"]:
            label = r.upper()
            if r == "campania": label += " (Salerno)"
            if r == "calabria": label += " (Cosenza)"
            
            report += f"### 📍 {label}\n| Stato | Zona | Criticità |\n|---|---|---|\n"
            
            if not results[r]:
                report += "| 🟢 | - | Nessuna criticità rilevata |\n"
            else:
                for item in sorted(results[r], key=lambda x: x['zona']):
                    report += f"| {emoji_map.get(item['crit'], '⚪')} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"--- FINE: SA:{len(results['campania'])} CS:{len(results['calabria'])} BASI:{len(results['basilicata'])} ---")

if __name__ == "__main__":
    SudAlertV14().process()
