import requests
from datetime import datetime, timedelta
import json
import os

class SudAlertPredictive:
    def __init__(self):
        # Zone di interesse
        self.zone_salerno = ["3", "5", "6", "7", "8"]
        self.zone_cosenza = ["1", "2"]
        self.zone_basilicata = ["A1", "A2", "B", "C", "D", "E1", "E2"]
        
        self.repo_raw_base = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/"
        self.repo_api_commits = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def get_latest_data(self):
        """Tenta di trovare il file in 3 modi diversi"""
        print(f"[{datetime.now().strftime('%H:%M')}] Avvio ricerca bollettino 2026...")

        # Metodo 1: Ricerca tramite gli ultimi 5 commits (Più affidabile)
        try:
            res = requests.get(self.repo_api_commits, timeout=10)
            commits = res.json()
            for commit in commits:
                sha = commit['sha']
                detail = requests.get(f"https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits/{sha}").json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    if fname.endswith('.json') and fname.startswith('202'):
                        print(f"✅ Trovato tramite Commit: {fname}")
                        return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"⚠️ Metodo Commits fallito: {e}")

        # Metodo 2: Tentativo predittivo (Oggi e Ieri)
        # I bollettini sono spesso 20260115_1430.json o 20260115_1500.json
        for d in [0, 1]:
            target_date = (datetime.now() - timedelta(days=d)).strftime("%Y%m%d")
            # Proviamo gli orari di pubblicazione standard (14:30, 15:00, 15:30, 16:00)
            for hhmm in ["1430", "1500", "1530", "1600", "1630"]:
                try_url = f"{self.repo_raw_base}{target_date}_{hhmm}.json"
                r = requests.get(try_url, timeout=5)
                if r.status_code == 200:
                    print(f"✅ Trovato tramite Tentativo Predittivo: {target_date}_{hhmm}.json")
                    return r.json(), f"{target_date}_{hhmm}.json"
        
        return None, None

    def get_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(stato).upper(), "⚪")

    def process(self):
        data, filename = self.get_latest_data()
        
        if not data:
            print("❌ ERRORE: Impossibile trovare un bollettino valido per ieri o oggi.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        count_alert = 0

        # Parsing dati
        for area in data.get("allerte", []):
            cod = area.get("codice", "")
            crit = area.get("criticita_idrogeologica", "VERDE")
            if crit != "VERDE": count_alert += 1
            
            if "CAM-" in cod:
                z = cod.split("-")[1]
                if z in self.zone_salerno: results["campania"].append({"zona": z, "crit": crit})
            elif "CAL-" in cod:
                z = cod.split("-")[1]
                if z in self.zone_cosenza: results["calabria"].append({"zona": z, "crit": crit})
            elif "BASI-" in cod:
                z = cod.split("-")[1]
                if z in self.zone_basilicata: results["basilicata"].append({"zona": z, "crit": crit})

        # Generazione Report Markdown
        report = f"# 🌩️ Sistema Vigilanza Sud Italia\n\n"
        report += f"**Data Report:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        report += f"**File Sorgente:** `{filename}`\n"
        report += f"**Zone con Allerta:** {'✅ Nessuna' if count_alert == 0 else f'⚠️ {count_alert} aree a rischio'}\n\n"

        for reg, items in results.items():
            report += f"### 📍 {reg.upper()}\n"
            report += "| Stato | Zona | Criticità |\n|---|---|---|\n"
            for i in items:
                report += f"| {self.get_emoji(i['crit'])} | **{i['zona']}** | {i['crit']} |\n"
            report += "\n"

        # Salvataggio
        with open("README.md", "w", encoding="utf-8") as f: f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j: json.dump(results, j, indent=4)
        print(f"🚀 Dashboard aggiornata con {filename}")

if __name__ == "__main__":
    SudAlertPredictive().process()
