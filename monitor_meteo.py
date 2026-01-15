import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

class SouthAlertMap:
    def __init__(self):
        # CONFIGURAZIONE FILTRI
        self.zone_campania_salerno = {"3": "Penisola Sorrentino-Amalfitana", "5": "Tusciano e Alto Sele", "6": "Piana Sele e Alto Cilento", "7": "Tanagro", "8": "Basso Cilento"}
        self.zone_calabria_cosenza = {"1": "Versante Tirrenico Settentrionale (CS)", "2": "Versante Jonico Settentrionale (CS)"}
        self.zone_basilicata = {"A1": "Bacini Agri e Sinni (M)", "A2": "Bacini Agri e Sinni (P)", "B": "Bradano", "C": "Basento", "D": "Sinni e Cavone", "E1": "Ofanto", "E2": "Sele"}
        
        # URL - Proviamo prima 'main' che è lo standard attuale
        self.url_dpc = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/main/bollettino.json"
        self.url_dpc_alt = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/bollettino.json"
        
        self.urls_regioni = {
            "campania": "https://bollettinimeteo.regione.campania.it/?cat=3",
            "calabria": "https://www.protezionecivilecalabria.it/",
            "basilicata": "https://protezionecivile.regione.basilicata.it/"
        }

    def get_color_emoji(self, stato):
        mapping = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        return mapping.get(stato.upper() if stato else "", "⚪")

    def fetch_dpc_json(self):
        """Tenta di scaricare il JSON nazionale con fallback del branch"""
        for url in [self.url_dpc, self.url_dpc_alt]:
            try:
                print(f"Tentativo download dati nazionali da: {url}")
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                print(f"Errore su {url}: {e}")
        return None

    def get_latest_links(self):
        links = {"campania": "#", "calabria": "#", "basilicata": "#"}
        try:
            # Campania
            r = requests.get(self.urls_regioni["campania"], timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            links["campania"] = soup.find('article').find('a')['href']
            # Calabria
            r_cal = requests.get(self.urls_regioni["calabria"], timeout=10)
            for a in BeautifulSoup(r_cal.text, 'html.parser').find_all('a', href=True):
                if 'bollettino' in a['href'].lower():
                    links["calabria"] = a['href'] if a['href'].startswith('http') else self.urls_regioni["calabria"] + a['href']
                    break
        except: pass
        return links

    def process_data(self):
        raw_data = self.fetch_dpc_json()
        if not raw_data:
            print("ERRORE CRITICO: Impossibile recuperare i dati nazionali DPC.")
            return

        links = self.get_latest_links()
        results = {"campania": [], "calabria": [], "basilicata": []}
        
        report = f"# 🗺️ Mappa Allerte: Campania, Calabria, Basilicata\n\n"
        report += f"**Aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

        def extract_region(prefix, filter_dict, region_key):
            temp_report = ""
            # Lo script cerca all'interno della lista 'allerte' del JSON nazionale
            for area in raw_data.get("allerte", []):
                cod = area.get("codice", "")
                if f"{prefix}-" in cod:
                    num = cod.replace(f"{prefix}-", "")
                    if num in filter_dict or not filter_dict:
                        crit = area.get('criticita_idrogeologica', 'VERDE')
                        emoji = self.get_color_emoji(crit)
                        desc = filter_dict.get(num, f"Zona {num}")
                        temp_report += f"| {emoji} | **{num}** | {desc} | {crit} |\n"
                        results[region_key].append({"zona": num, "crit": crit, "desc": desc})
            return temp_report

        # Sezioni Report
        report += "### 🍋 Campania (Salerno)\n| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract_region("CAM", self.zone_campania_salerno, "campania")
        
        report += "\n### 🌶️ Calabria (Cosenza)\n| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract_region("CAL", self.zone_calabria_cosenza, "calabria")
        
        report += "\n### 🌲 Basilicata (Tutte)\n| | Zona | Territorio | Stato |\n|---|---|---|---|\n"
        report += extract_region("BASI", self.zone_basilicata, "basilicata")

        # Salvataggio
        with open("README.md", "w", encoding="utf-8") as f: f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j: json.dump(results, j, indent=4)
        print("Successo: README.md e data_mappa.json aggiornati.")

if __name__ == "__main__":
    SouthAlertMap().process_data()
