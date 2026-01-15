import requests
from datetime import datetime
import json
import os

class SouthAlertHub2026:
    def __init__(self):
        # Configurazione Zone
        self.filtri = {
            "CAMPANIA": {"zone": ["3", "5", "6", "7", "8"], "label": "Salerno"},
            "CALABRIA": {"zone": ["1", "2"], "label": "Cosenza"},
            "BASILICATA": {"zone": ["A1", "A2", "B", "C", "D", "E1", "E2"], "label": "Tutta la Regione"}
        }
        
        # Repository DPC (Proviamo prima 'main', poi 'master')
        self.repos = [
            {
                "name": "Criticità Idrogeologica",
                "api": "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/contents/files",
                "raw": "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/{branch}/files/"
            },
            {
                "name": "Vigilanza Meteorologica",
                "api": "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/contents/files",
                "raw": "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/{branch}/files/"
            }
        ]

    def get_latest_valid_data(self, repo_config):
        """Cerca l'ultimo file navigando tra i branch main e master"""
        for branch in ['main', 'master']:
            try:
                print(f"Ricerca in {repo_config['name']} (branch: {branch})...")
                # Chiediamo esplicitamente il branch all'API
                api_url = f"{repo_config['api']}?ref={branch}"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    files = response.json()
                    # Filtriamo i JSON e ordiniamo per data (nome file)
                    json_files = sorted([f['name'] for f in files if f['name'].endswith('.json')], reverse=True)
                    
                    if json_files:
                        latest_file = json_files[0]
                        # Verifichiamo se il file è recente (dell'anno corrente)
                        if latest_file.startswith(str(datetime.now().year)):
                            full_url = repo_config['raw'].format(branch=branch) + latest_file
                            print(f"✅ Trovato file recente: {latest_file}")
                            return requests.get(full_url).json(), latest_file
                        else:
                            print(f"⚠️ File trovato ({latest_file}) troppo vecchio. Salto branch...")
            except Exception as e:
                print(f"❌ Errore branch {branch}: {e}")
        return None, None

    def get_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(stato).upper(), "⚪")

    def process(self):
        print(f"--- AVVIO MONITORAGGIO SUD ITALIA {datetime.now().year} ---")
        
        # Recuperiamo i dati dal repository Criticità (il più importante per i colori mappa)
        data_crit, filename = self.get_latest_valid_data(self.repos[0])
        
        if not data_crit:
            print("❌ Impossibile trovare dati recenti del 2026. Verifica i repository DPC.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Costruzione Dashboard
        report = f"# 🌩️ Sistema Vigilanza Sud Italia\n\n"
        report += f"**Bollettino del:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        report += f"**File Sorgente:** `{filename}`\n\n"

        # Parsing dati per le zone specifiche
        for area in data_crit.get("allerte", []):
            codice = area.get("codice", "")
            for reg_key, config in self.filtri.items():
                prefix = reg_key[:3] if reg_key != "BASILICATA" else "BASI"
                if f"{prefix}-" in codice:
                    zona_num = codice.split("-")[1]
                    if zona_num in config["zone"]:
                        crit = area.get("criticita_idrogeologica", "VERDE")
                        results[reg_key.lower()].append({
                            "zona": zona_num,
                            "crit": crit,
                            "desc": config["zone"].get(zona_num, f"Zona {zona_num}") if isinstance(config["zone"], dict) else f"Zona {zona_num}"
                        })

        # Generazione README
        for reg_key in ["CAMPANIA", "CALABRIA", "BASILICATA"]:
            config = self.filtri[reg_key]
            items = results[reg_key.lower()]
            report += f"### 📍 {reg_key.capitalize()} ({config['label']})\n"
            report += "| Stato | Zona | Descrizione | Criticità |\n|---|---|---|---|\n"
            for item in items:
                desc = item['desc']
                report += f"| {self.get_emoji(item['crit'])} | **{item['zona']}** | {desc} | {item['crit']} |\n"
            report += "\n"

        # Salvataggio
        with open("README.md", "w", encoding="utf-8") as f: f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j: json.dump(results, j, indent=4)
        print("🚀 Dashboard e Mappa aggiornate con dati 2026!")

if __name__ == "__main__":
    SouthAlertHub2026().process()
