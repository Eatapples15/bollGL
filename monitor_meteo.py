import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

class SouthAlertMap:
    def __init__(self):
        # FILTRI RICHIESTI
        self.zone_campania_salerno = {
            "3": "Penisola Sorrentino-Amalfitana",
            "5": "Tusciano e Alto Sele",
            "6": "Piana Sele e Alto Cilento",
            "7": "Tanagro",
            "8": "Basso Cilento"
        }
        self.zone_calabria_cosenza = {
            "1": "Versante Tirrenico Settentrionale (CS)",
            "2": "Versante Jonico Settentrionale (CS)"
        }
        # Basilicata: Tutte le zone
        self.zone_basilicata = {
            "A1": "Bacini Agri e Sinni (Montagna)",
            "A2": "Bacini Agri e Sinni (Pianura)",
            "B": "Bacino del Bradano",
            "C": "Bacino del Basento",
            "D": "Bacini del Sinni e del Cavone",
            "E1": "Bacino dell'Ofanto",
            "E2": "Bacino del Sele"
        }
        
        self.urls = {
            "campania": "https://bollettinimeteo.regione.campania.it/?cat=3",
            "calabria": "https://www.protezionecivilecalabria.it/",
            "basilicata": "https://protezionecivile.regione.basilicata.it/",
            "dpc_json": "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/bollettino.json"
        }

    def get_color_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(stato.upper(), "⚪")

    def get_latest_links(self):
        """Recupera i link ai bollettini regionali"""
        links = {"campania": "#", "calabria": "#", "basilicata": "#"}
        try:
            # Campania
            r = requests.get(self.urls["campania"], timeout=10)
            links["campania"] = BeautifulSoup(r.text, 'html.parser').find('article').find('a')['href']
            # Calabria
            r = requests.get(self.urls["calabria"], timeout=10)
            for a in BeautifulSoup(r.text, 'html.parser').find_all('a', href=True):
                if 'bollettino' in a['href'].lower():
                    links["calabria"] = a['href'] if a['href'].startswith('http') else self.urls["calabria"] + a['href']
                    break
            # Basilicata
            links["basilicata"] = self.urls["basilicata"] # Portale principale
        except: pass
        return links

    def process_data(self):
        print("Elaborazione dati per Mappa 3 Regioni...")
        raw_data = requests.get(self.urls["dpc_json"]).json()
        links = self.get_latest_links()
        
        results = {"campania": [], "calabria": [], "basilicata": []}
        
        report = f"# 🗺️ Mappa Allerte: Campania, Calabria, Basilicata\n\n"
        report += f"**Aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

        # Funzione helper per estrarre e formattare
        def extract_region(prefix, filter_dict, region_key):
            temp_report = ""
            for area in raw_data.get("allerte", []):
                cod = area.get("codice", "")
                if f"{prefix}-" in cod:
                    num = cod.replace(f"{prefix}-", "")
                    if num in filter_dict or not filter_dict: # If filter_dict is empty, take all
                        crit = area['criticita_idrogeologica']
                        emoji = self.get_color_emoji(crit)
                        desc = filter_dict.get(num, f"Zona {num}")
                        temp_report += f"| {emoji} | **{num}** | {desc} | {crit} |\n"
                        results[region_key].append({"zona": num, "crit": crit, "desc": desc})
            return temp_report

        # --- CAMPANIA (SALERNO) ---
        report += "### 🍋 Campania (Provincia di Salerno)\n"
        report += "| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract_region("CAM", self.zone_campania_salerno, "campania")
        report += f"\n🔗 [Bollettino Campania]({links['campania']})\n\n---\n"

        # --- CALABRIA (COSENZA) ---
        report += "### 🌶️ Calabria (Provincia di Cosenza)\n"
        report += "| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract_region("CAL", self.zone_calabria_cosenza, "calabria")
        report += f"\n🔗 [Bollettino Calabria]({links['calabria']})\n\n---\n"

        # --- BASILICATA (TUTTE) ---
        report += "### 🌲 Basilicata (Tutte le zone)\n"
        report += "| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract_region("BASI", self.zone_basilicata, "basilicata")
        report += f"\n🔗 [Bollettino Basilicata]({links['basilicata']})\n\n"

        report += "\n*Dati generati per alimentare la mappa dei rischi zonale.*"

        # Salvataggio README per visualizzazione GitHub
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)
            
        # INNOVAZIONE: Salvataggio JSON per uso futuro con mappa dinamica
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)

if __name__ == "__main__":
    SouthAlertMap().process_data()
