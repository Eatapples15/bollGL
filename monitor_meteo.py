import requests
from datetime import datetime
import json
import os
import re

class DPCDataExplorer:
    def __init__(self):
        # Filtri Territoriali
        self.filtri = {
            "CAMPANIA": {"zone": ["3", "5", "6", "7", "8"], "label": "Salerno"},
            "CALABRIA": {"zone": ["1", "2"], "label": "Cosenza"},
            "BASILICATA": {"zone": ["A1", "A2", "B", "C", "D", "E1", "E2"], "label": "Tutta la Regione"}
        }
        
        # URL API di GitHub per elencare i file nelle cartelle che hai linkato
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/contents/files"
        self.raw_base_url = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/"

    def get_latest_file_url(self):
        """Trova il nome del file JSON più recente nella cartella /files"""
        print(f"[{datetime.now().strftime('%H:%M')}] Ricerca ultimo bollettino nel repository DPC...")
        try:
            response = requests.get(self.repo_api, timeout=15)
            response.raise_for_status()
            files = response.json()
            
            # Filtra solo i file .json e ordinali per nome (che contiene la data)
            json_files = [f['name'] for f in files if f['name'].endswith('.json')]
            if not json_files:
                return None
            
            latest_file = sorted(json_files, reverse=True)[0]
            print(f"File più recente individuato: {latest_file}")
            return self.raw_base_url + latest_file
        except Exception as e:
            print(f"Errore nella ricerca file: {e}")
            return None

    def get_color_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(stato).upper(), "⚪")

    def process(self):
        latest_url = self.get_latest_file_url()
        if not latest_url:
            return

        try:
            data = requests.get(latest_url).json()
        except:
            print("Errore nel parsing del JSON.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        report = f"# 🌩️ Sistema Vigilanza - Sud Italia\n\n"
        report += f"**Dati aggiornati al:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        report += f"**Fonte DPC:** [{latest_url.split('/')[-1]}]({latest_url})\n\n"

        # Estrazione Dati per le 3 Regioni
        for area in data.get("allerte", []):
            codice = area.get("codice", "")
            # Identifica la regione dal prefisso (CAM, CAL, BASI)
            for reg_key, config in self.filtri.items():
                prefix = reg_key[:3] if reg_key != "BASILICATA" else "BASI"
                
                if f"{prefix}-" in codice:
                    zona_num = codice.split("-")[1]
                    if zona_num in config["zone"]:
                        crit = area.get("criticita_idrogeologica", "VERDE")
                        results[reg_key.lower()].append({
                            "zona": zona_num,
                            "crit": crit,
                            "desc": f"Zona {zona_num}"
                        })

        # Generazione tabelle per il README
        for reg_key in ["CAMPANIA", "CALABRIA", "BASILICATA"]:
            config = self.filtri[reg_key]
            items = results[reg_key.lower()]
            
            report += f"### 📍 {reg_key.capitalize()} ({config['label']})\n"
            report += "| Stato | Zona | Criticità |\n|---|---|---|\n"
            for item in items:
                report += f"| {self.get_color_emoji(item['crit'])} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        # Salvataggio file per l'HTML e GitHub
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        print("Aggiornamento completato con successo.")

if __name__ == "__main__":
    DPCDataExplorer().process()
