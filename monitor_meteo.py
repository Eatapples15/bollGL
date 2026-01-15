import requests
from datetime import datetime
import json
import os

class SudAlertFinal2026:
    def __init__(self):
        # Filtri precisi
        self.targets = {
            "CAMPANIA": ["3", "5", "6", "7", "8"], # Salerno
            "CALABRIA": ["1", "2"],              # Cosenza
            "BASILICATA": ["A1", "A2", "B", "C", "D", "E1", "E2"]
        }
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def get_topo_json_url(self):
        """Trova l'ultimo indice e pesca il link del TopoJSON di domani"""
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    # Cerchiamo il file indice (es: 20260114_1439.json)
                    if fname.endswith('.json') and "_" in fname and "tomorrow" not in fname and "style" not in fname:
                        print(f"✅ Indice trovato: {fname}")
                        meta_data = requests.get(f['raw_url']).json()
                        # Estraiamo il link al TopoJSON di domani (vigilanza)
                        topo_url = meta_data.get("tomorrow", {}).get("topo_json")
                        return topo_url, fname
        except Exception as e:
            print(f"❌ Errore ricerca: {e}")
        return None, None

    def normalize_status(self, val):
        """Converte i codici numerici o stringa in testo chiaro"""
        s = str(val).upper()
        if s == "1" or "VERDE" in s: return "VERDE"
        if s == "2" or "GIALLA" in s: return "GIALLA"
        if s == "3" or "ARANCIONE" in s: return "ARANCIONE"
        if s == "4" or "ROSSA" in s: return "ROSSA"
        return "VERDE"

    def process(self):
        topo_url, filename = self.get_topo_json_url()
        if not topo_url:
            print("❌ Nessun TopoJSON trovato.")
            return

        print(f"📥 Scaricamento dati mappa da: {topo_url}")
        topo_data = requests.get(topo_url).json()

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Nel TopoJSON del DPC, le geometrie sono sotto objects -> bollettino -> geometries
        try:
            geometries = topo_data['objects']['bollettino']['geometries']
        except KeyError:
            # Fallback se la struttura cambia
            geometries = []
            print("⚠️ Struttura TopoJSON imprevista.")

        for geo in geometries:
            p = geo.get("properties", {})
            raw_code = str(p.get("Codice_Area", "")).upper()
            
            # Estrazione criticità idrogeologica
            crit = self.normalize_status(p.get("Idro", "VERDE"))

            # Pulizia codice (es. CAM-03 -> 3)
            clean_z = raw_code.split("-")[-1] if "-" in raw_code else raw_code
            if clean_z.isdigit(): clean_z = str(int(clean_z))

            # Matching Regioni
            reg = ""
            if "CAM" in raw_code: reg = "campania"
            elif "CAL" in raw_code: reg = "calabria"
            elif "BASI" in raw_code: reg = "basilicata"

            if reg in results:
                # Filtro Salerno e Cosenza
                if reg == "campania" and clean_z in self.targets["CAMPANIA"]:
                    results[reg].append({"zona": clean_z, "crit": crit})
                elif reg == "calabria" and clean_z in self.targets["CALABRIA"]:
                    results[reg].append({"zona": clean_z, "crit": crit})
                elif reg == "basilicata": # Basilicata tutta
                    results[reg].append({"zona": clean_z, "crit": crit})

        # --- GENERAZIONE REPORT ---
        report = f"# 🌩️ Monitoraggio Sud Italia\n\n**Analisi Bollettino:** `{filename}`\n"
        report += f"**Aggiornato al:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

        for r in ["campania", "calabria", "basilicata"]:
            label = "CAMPANIA (Salerno)" if r == "campania" else "CALABRIA (Cosenza)" if r == "calabria" else "BASILICATA"
            report += f"### 📍 {label}\n| Stato | Zona | Criticità |\n|---|---|---|\n"
            if not results[r]:
                report += "| 🟢 | - | Nessun fenomeno significativo |\n"
            else:
                # Rimuovi duplicati e ordina
                unique_zones = {z['zona']: z['crit'] for z in results[r]}
                for z in sorted(unique_zones.keys()):
                    emoji = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}.get(unique_zones[z], "⚪")
                    report += f"| {emoji} | **{z}** | {unique_zones[z]} |\n"
            report += "\n"

        with open("README.md", "w", encoding="utf-8") as f: f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j: json.dump(results, j, indent=4)
        
        print(f"🚀 Completato! Trovate {len(geometries)} aree totali.")

if __name__ == "__main__":
    SudAlertFinal2026().process()
