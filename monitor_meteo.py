import requests
from datetime import datetime
import json
import os
import time
import random

class SudAlertForceUpdate:
    def __init__(self):
        # Configurazione Target
        self.targets = {
            "CAMPANIA": ["3", "5", "6", "7", "8"], # Salerno
            "CALABRIA": ["1", "2"],              # Cosenza
            "BASILICATA": ["A1", "A2", "B", "C", "D", "E1", "E2"]
        }
        
        # Keyword per recupero geografico (se il prefisso manca)
        self.geo_map = {
            "CAMPANIA": ["(SA)", "SALERNO", "AMALFI", "AGROPOLI", "SAPRI", "EBOLI"],
            "CALABRIA": ["(CS)", "COSENZA", "PAOLA", "RENDE", "CASTROVILLARI", "ROSSANO"],
            "BASILICATA": ["(PZ)", "(MT)", "POTENZA", "MATERA"]
        }
        
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def get_latest_data(self):
        """Ottiene il link al TopoJSON più recente"""
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    # Cerchiamo l'indice principale o il tomorrow diretto
                    if "tomorrow.json" in fname and "202" in fname:
                        print(f"✅ File rilevato: {fname}")
                        return requests.get(f['raw_url']).json(), fname
        except Exception as e:
            print(f"❌ Errore critico: {e}")
        return None, None

    def clean_zone(self, text):
        """Pulisce il nome della zona per estrarre il codice (es. Basi-A1 -> A1)"""
        t = str(text).upper().replace("ZONA", "").replace("BASI-", "").replace("CAM-", "").replace("CAL-", "").replace("-", "").strip()
        if t.isdigit(): t = str(int(t))
        return t

    def identify_region(self, props):
        """Determina la regione analizzando nome zona e comuni"""
        name = str(props.get("Nome zona", "")).upper()
        comuni = str(props.get("Comuni", "")).upper()
        
        if "BASI" in name: return "BASILICATA"
        if "CAM" in name or any(k in comuni for k in self.geo_map["CAMPANIA"]): return "CAMPANIA"
        if "CAL" in name or any(k in comuni for k in self.geo_map["CALABRIA"]): return "CALABRIA"
        if any(k in comuni for k in self.geo_map["BASILICATA"]): return "BASILICATA"
        return "UNKNOWN"

    def get_color(self, props):
        """Estrae il colore basandosi sui testi dello style.json"""
        # Controlliamo 'Rappresentata nella mappa' o 'Per rischio idrogeologico'
        txt = str(props.get("Rappresentata nella mappa", props.get("Per rischio idrogeologico", "VERDE"))).upper()
        if "ROSSA" in txt or "ELEVATA" in txt: return "ROSSA"
        if "ARANCIONE" in txt or "MODERATA" in txt: return "ARANCIONE"
        if "GIALLA" in txt or "ORDINARIA" in txt: return "GIALLA"
        return "VERDE"

    def process(self):
        data, fname = self.get_latest_data()
        if not data: return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Parsing TopoJSON
        obj_key = list(data['objects'].keys())[0]
        geometries = data['objects'][obj_key]['geometries']

        for geo in geometries:
            p = geo.get("properties", {})
            region = self.identify_region(p)
            zone_code = self.clean_zone(p.get("Nome zona", ""))
            color = self.get_color(p)

            if region in self.targets:
                if zone_code in self.targets[region] or region == "BASILICATA":
                    results[region.lower()].append({"zona": zone_code, "crit": color})

        # Deduplicazione
        for r in ["campania", "calabria", "basilicata"]:
            unique = {z['zona']: z['crit'] for z in results[r]}
            results[r] = [{"zona": k, "crit": v} for k, v in sorted(unique.items())]

        # INNOVATIVO: Force Update Metadata
        # Inseriamo un ID unico che cambia ad ogni millisecondo per forzare il push di Git
        results["force_metadata"] = {
            "timestamp_ns": time.time_ns(),
            "update_id": f"REF-{random.randint(1000, 9999)}",
            "last_check": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            "source": fname
        }

        # Scrittura JSON
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        # Scrittura README
        self.update_readme(results)
        print(f"🚀 Update completato. SA:{len(results['campania'])} | CS:{len(results['calabria'])} | BASI:{len(results['basilicata'])}")

    def update_readme(self, results):
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        meta = results["force_metadata"]
        
        report = f"# 🌩️ Monitoraggio Meteo Sud Italia\n\n"
        report += f"**Stato:** AGGIORNATO | **Update ID:** `{meta['update_id']}`\n"
        report += f"**Ultima verifica:** {now} | **Sorgente:** `{meta['source']}`\n\n"
        
        emoji = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        
        for r in ["campania", "calabria", "basilicata"]:
            title = r.upper()
            if r == "campania": title += " (Salerno)"
            elif r == "calabria": title += " (Cosenza)"
            
            report += f"### 📍 {title}\n| Stato | Zona | Criticità |\n|---|---|---|\n"
            if not results[r]:
                report += "| 🟢 | - | Nessuna allerta significativa |\n"
            else:
                for item in results[r]:
                    report += f"| {emoji.get(item['crit'], '⚪')} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)

if __name__ == "__main__":
    SudAlertForceUpdate().process()
