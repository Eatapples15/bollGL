import requests
from datetime import datetime
import json
import os

class SudAlertUltimaGenerazione:
    def __init__(self):
        # Filtri Territoriali
        self.zone_salerno = ["3", "5", "6", "7", "8"]
        self.zone_cosenza = ["1", "2"]
        self.zone_basilicata = ["A1", "A2", "B", "C", "D", "E1", "E2"]
        
        # Repository DPC
        self.repo_owner = "pcm-dpc"
        self.repo_name = "DPC-Bollettini-Criticita-Idrogeologica-Idraulica"
        
    def get_latest_file_via_commits(self):
        """
        Innova: Usa l'API dei Commits per trovare l'ultimo file caricato.
        Evita il limite dei 1000 file delle API standard.
        """
        print(f"[{datetime.now().strftime('%H:%M')}] Ricerca bollettino 2026 tramite Git Commits...")
        
        # Chiediamo l'ultimo commit che ha toccato la cartella 'files'
        api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits?path=files&per_page=1"
        
        try:
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            last_commit = response.json()[0]
            
            # Ora chiediamo i dettagli di quel commit per vedere il nome del file
            commit_sha = last_commit['sha']
            detail_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{commit_sha}"
            detail_res = requests.get(detail_url, timeout=15)
            files_changed = detail_res.json()['files']
            
            # Cerchiamo il file .json nella cartella files
            for f in files_changed:
                filename = f['filename']
                if filename.startswith("files/") and filename.endswith(".json"):
                    raw_url = f['raw_url']
                    clean_name = filename.split("/")[-1]
                    print(f"✅ Trovato Bollettino Attuale: {clean_name}")
                    return raw_url, clean_name
                    
        except Exception as e:
            print(f"❌ Errore durante la ricerca: {e}")
            
        # Fallback estremo: il file 'bollettino.json' che a volte viene aggiornato come link statico
        print("⚠️ Provo fallback su file statico...")
        return f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/master/bollettino.json", "bollettino.json"

    def get_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(stato).upper(), "⚪")

    def process(self):
        raw_url, filename = self.get_latest_file_via_commits()
        
        try:
            data = requests.get(raw_url).json()
        except:
            print("❌ Errore nel download del contenuto JSON.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Generazione Report
        report = f"# 🌩️ Sistema Vigilanza Sud Italia\n\n"
        report += f"**Ultimo aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        report += f"**File Analizzato:** `{filename}`\n\n"
        report += "> [!TIP]\n> La mappa sottostante si aggiorna automaticamente in base a questi dati.\n\n"

        for area in data.get("allerte", []):
            codice = area.get("codice", "")
            crit = area.get("criticita_idrogeologica", "VERDE")
            
            # CAMPANIA -> SALERNO
            if "CAM-" in codice:
                z = codice.split("-")[1]
                if z in self.zone_salerno:
                    results["campania"].append({"zona": z, "crit": crit})
            
            # CALABRIA -> COSENZA
            elif "CAL-" in codice:
                z = codice.split("-")[1]
                if z in self.zone_cosenza:
                    results["calabria"].append({"zona": z, "crit": crit})
            
            # BASILICATA -> TUTTE
            elif "BASI-" in codice:
                z = codice.split("-")[1]
                if z in self.zone_basilicata:
                    results["basilicata"].append({"zona": z, "crit": crit})

        # Costruzione Tabelle README
        for reg, items in results.items():
            if items:
                report += f"### 📍 {reg.upper()}\n"
                report += "| Stato | Zona | Criticità |\n|---|---|---|\n"
                for i in items:
                    report += f"| {self.get_emoji(i['crit'])} | **{i['zona']}** | {i['crit']} |\n"
                report += "\n"

        # Salvataggio
        with open("README.md", "w", encoding="utf-8") as f: f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j: json.dump(results, j, indent=4)
        print(f"🚀 Dashboard aggiornata con successo alle {datetime.now().strftime('%H:%M')}")

if __name__ == "__main__":
    SudAlertUltimaGenerazione().process()
