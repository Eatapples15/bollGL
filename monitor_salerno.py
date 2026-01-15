import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

class SalernoAlertSystem:
    def __init__(self):
        self.zone_salerno = {
            "3": "Penisola Sorrentino-Amalfitana, Monti di Sarno e Monti Picentini",
            "5": "Tusciano e Alto Sele",
            "6": "Piana Sele e Alto Cilento",
            "7": "Tanagro",
            "8": "Basso Cilento"
        }
        self.url_campania = "https://bollettinimeteo.regione.campania.it/?cat=3"
        self.url_dpc_github = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/bollettino.json"
        self.log_file = "README.md" # Useremo il README come dashboard principale

    def fetch_data(self):
        print("Recupero dati in corso...")
        
        # 1. Info Regione Campania
        res_reg = requests.get(self.url_campania, timeout=15)
        soup = BeautifulSoup(res_reg.text, 'html.parser')
        latest_post = soup.find('article')
        titolo_reg = latest_post.find('h2').text.strip()
        link_reg = latest_post.find('a')['href']

        # 2. Info DPC (Dati strutturati)
        res_nat = requests.get(self.url_dpc_github, timeout=15)
        data_nat = res_nat.json()
        
        # Filtraggio zone Salerno
        allerte_salerno = []
        for area in data_nat.get("allerte", []):
            codice = area.get("codice", "")
            if "CAM-" in codice:
                num = codice.split("-")[1]
                if num in self.zone_salerno:
                    allerte_salerno.append({
                        "zona": num,
                        "desc": self.zone_salerno[num],
                        "idro": area.get("criticita_idrogeologica", "Verde"),
                        "temp": area.get("criticita_per_temporali", "Verde"),
                        "idra": area.get("criticita_idraulica", "Verde")
                    })
        return titolo_reg, link_reg, allerte_salerno

    def update_readme(self, titolo, link, allerte):
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        content = f"# 🌩️ Bollettino Criticità Salerno\n\n"
        content += f"**Ultimo controllo automatico:** {now}\n\n"
        content += f"## 📢 Ultimo Avviso Regionale\n"
        content += f"**[{titolo}]({link})**\n\n"
        content += f"## 📍 Dettaglio per Zone (Provincia di Salerno)\n\n"
        content += "| Zona | Descrizione Territoriale | Idrogeologica | Temporali | Idraulica |\n"
        content += "|---|---|---|---|---|\n"
        
        for a in allerte:
            content += f"| **{a['zona']}** | {a['desc']} | {a['idro']} | {a['temp']} | {a['idra']} |\n"
        
        content += "\n\n---\n*Dati aggiornati automaticamente tramite GitHub Actions e DPC Open Data.*"
        
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(content)

if __name__ == "__main__":
    bot = SalernoAlertSystem()
    t, l, a = bot.fetch_data()
    bot.update_readme(t, l, a)
    print("Dashboard aggiornata con successo!")
