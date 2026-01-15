import requests
from datetime import datetime
import json
import os

class SudAlertFinalMaster:
    def __init__(self):
        # Filtri Territoriali
        self.targets = {
            "CAMPANIA": ["3", "5", "6", "7", "8"], # Salerno
            "CALABRIA": ["1", "2"],              # Cosenza
            "BASILICATA": ["A1", "A2", "B", "C", "D", "E1", "E2"]
        }
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def get_data_from_dpc(self):
        """Trova i dati cercando sia l'indice che i file diretti"""
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                files = detail.get('files', [])
                
                # 1. Cerchiamo prima il TopoJSON di 'tomorrow' (più preciso)
                for f in files:
                    fname = f['filename'].split('/')[-1]
                    if "tomorrow.json" in fname and "202" in fname:
                        print(f"✅ TopoJSON diretto trovato: {fname}")
                        return requests.get(f['raw_url']).json(), fname

                # 2. Se non c'è il diretto, cerchiamo l'indice
                for f in files:
                    fname = f['filename'].split('/')[-1]
                    if fname.endswith('.json') and "_" in fname and "style" not in fname and "today" not in fname and "tomorrow" not in fname:
                        print(f"✅ Indice trovato: {fname}. Estraggo link...")
                        meta = requests.get(f['raw_url']).json()
                        topo_url = meta.get("tomorrow", {}).get("topo_json")
                        if topo_url:
                            return requests.get(topo_url).json(), fname
        except Exception as e:
            print(f"❌ Errore critico: {e}")
        return None, None

    def normalize_status(self, val):
        s = str(val).upper()
        if s in ["1", "VERDE"]: return "VERDE"
        if s in ["2", "GIALLA"]: return "GIALLA"
        if s in ["3", "ARANCIONE"]: return "ARANCIONE"
        if s in ["4", "ROSSA"]: return "ROSSA"
        return "VERDE"

    def process(self):
        data, filename = self.get_data_from_dpc()
        if not data:
            print("❌ Impossibile trovare bollettini validi.")
            return

        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Estrazione Geometrie (TopoJSON standard DPC)
        try:
            # Prova i due rami comuni del TopoJSON DPC
            items = []
            if 'objects' in data:
                key = list(data['objects'].keys())[0]
                items = data['objects'][key]['geometries']
            elif 'features' in data:
                items = data['features']
            
            print(f"Analisi di {len(items)} aree geografiche...")

            for item in items:
                p = item.get("properties", {})
                # Campi comuni: Codice_Area, Idro, Idra, Stato
                raw_code = str(p.get("Codice_Area", p.get("codice", ""))).upper()
                crit = self.normalize_status(p.get("Idro", p.get("Idrogeologica", "VERDE")))

                # Pulizia codice
                clean_z = raw_code.split("-")[-1] if "-" in raw_code else raw_code
                if clean_z.isdigit(): clean_z = str(int(clean_z))

                # Identificazione Regione
                reg_found = ""
                if "CAM" in raw_code: reg_found = "campania"
                elif "CAL" in raw_code: reg_found = "calabria"
                elif "BASI" in raw_code: reg_found = "basilicata"

                if reg_found in results:
                    if reg_found == "campania" and clean_z in self.targets["CAMPANIA"]:
                        results[reg_found].append({"zona": clean_z, "crit": crit})
                    elif reg_found == "calabria" and clean_z in self.targets["CALABRIA"]:
                        results[reg_found].append({"zona": clean_z, "crit": crit})
                    elif reg_found == "basilicata":
                        results[reg_found].append({"zona": clean_z, "crit": crit})

        except Exception as e:
            print(f"⚠️ Errore durante il parsing: {e}")

        # --- GENERAZIONE REPORT ---
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        report = f"# 🌩️ Monitoraggio Protezione Civile Sud Italia\n\n"
        report += f"**Bollettino:** `{filename}`\n"
        report += f"**Aggiornamento:** {now_str}\n\n"

        for r in ["campania", "calabria", "basilicata"]:
            label = "CAMPANIA (Salerno)" if r == "campania" else "CALABRIA (Cosenza)" if r == "calabria" else "BASILICATA"
            report += f"### 📍 {label}\n| Stato | Zona | Criticità |\n|---|---|---|\n"
            
            # Rimuove duplicati (una zona può avere più poligoni)
            unique = {z['zona']: z['crit'] for z in results[r]}
            if not unique:
                report += "| 🟢 | - | Nessuna allerta |\n"
            else:
                for z in sorted(unique.keys()):
                    emoji = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}.get(unique[z], "⚪")
                    report += f"| {emoji} | **{z}** | {unique[z]} |\n"
            report += "\n"

        # Salvataggio
        with open("README.md", "w", encoding="utf-8") as f: f.write(report)
        with open("data_mappa.json", "w", encoding="utf-8") as j: json.dump(results, j, indent=4)
        print(f"🚀 Dashboard aggiornata con successo!")

if __name__ == "__main__":
    SudAlertFinalMaster().process()
