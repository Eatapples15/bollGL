import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os

class SouthAlertMap:
    def __init__(self):
        self.zone_campania_salerno = {"3": "Penisola Sorrentino-Amalfitana", "5": "Tusciano e Alto Sele", "6": "Piana Sele e Alto Cilento", "7": "Tanagro", "8": "Basso Cilento"}
        self.zone_calabria_cosenza = {"1": "Versante Tirrenico Settentrionale (CS)", "2": "Versante Jonico Settentrionale (CS)"}
        self.zone_basilicata = {"A1": "Bacini Agri e Sinni (M)", "A2": "Bacini Agri e Sinni (P)", "B": "Bradano", "C": "Basento", "D": "Sinni e Cavone", "E1": "Ofanto", "E2": "Sele"}
        
        # URL DPC (Protezione Civile Nazionale)
        self.url_dpc = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/bollettino.json"
        
        self.urls_regioni = {
            "campania": "https://bollettinimeteo.regione.campania.it/?cat=3",
            "calabria": "https://www.protezionecivilecalabria.it/"
        }

    def get_color_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(str(stato).upper(), "⚪")

    def process_data(self):
        print("Avvio elaborazione dati...")
        try:
            r = requests.get(self.url_dpc, timeout=20)
            r.raise_for_status()
            raw_data = r.json()
        except Exception as e:
            print(f"Errore download DPC: {e}")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Generazione Report Markdown
        report = f"# 🗺️ Mappa Allerte: Sud Italia\n\n"
        report += f"**Ultimo aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

        def extract(prefix, filter_dict, key):
            out = ""
            for area in raw_data.get("allerte", []):
                cod = area.get("codice", "")
                if f"{prefix}-" in cod:
                    num = cod.replace(f"{prefix}-", "")
                    if num in filter_dict:
                        crit = area.get('criticita_idrogeologica', 'VERDE')
                        results[key].append({"zona": num, "crit": crit, "desc": filter_dict[num]})
                        out += f"| {self.get_color_emoji(crit)} | **{num}** | {filter_dict[num]} | {crit} |\n"
            return out

        report += "### 🍋 Campania (Salerno)\n| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract("CAM", self.zone_campania_salerno, "campania")
        
        report += "\n### 🌶️ Calabria (Cosenza)\n| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract("CAL", self.zone_calabria_cosenza, "calabria")
        
        report += "\n### 🌲 Basilicata (Tutte)\n| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract("BASI", self.zone_basilicata, "basilicata")

        # SCRITTURA FILE
        base_path = os.getcwd()
        with open(os.path.join(base_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(report)
        with open(os.path.join(base_path, "data_mappa.json"), "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        print("File README.md e data_mappa.json generati correttamente.")

if __name__ == "__main__":
    SouthAlertMap().process_data()
