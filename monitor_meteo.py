import requests
from datetime import datetime
import json
import os

class ProtezioneCivileSudAlert:
    def __init__(self):
        # Mappatura Province Obiettivo
        self.provincia_salerno = ["SALERNO", "AMALFI", "AGROPOLI", "SAPRI", "EBOLI", "BATTIPAGLIA", "NOCERA", "VIETRI", "POSITANO"]
        self.provincia_cosenza = ["COSENZA", "PAOLA", "RENDE", "CASTROVILLARI", "CORIGLIANO", "ROSSANO", "SCALEA", "DIAMANTE"]
        
        # URL API GitHub per i bollettini
        self.repo_api = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/commits?path=files&per_page=5"

    def fetch_topo_json(self):
        """Naviga dall'indice al TopoJSON di domani"""
        try:
            res = requests.get(self.repo_api, timeout=15)
            commits = res.json()
            for commit in commits:
                detail = requests.get(commit['url']).json()
                for f in detail.get('files', []):
                    fname = f['filename'].split('/')[-1]
                    # Troviamo il file indice (es: 20260114_1439.json)
                    if fname.endswith('.json') and "_" in fname and len(fname.split('_')) == 2:
                        print(f"✅ Indice trovato: {fname}")
                        meta = requests.get(f['raw_url']).json()
                        # Puntiamo al bollettino di domani (previsionale)
                        return meta.get("tomorrow", {}).get("topo_json"), fname
        except Exception as e:
            print(f"❌ Errore ricerca: {e}")
        return None, None

    def get_alert_level(self, text):
        """Analizza il testo del rischio e restituisce il colore (basato su style.json)"""
        t = str(text).upper()
        if "ROSSA" in t or "ELEVATA" in t: return "ROSSA"
        if "ARANCIONE" in t or "MODERATA" in t: return "ARANCIONE"
        if "GIALLA" in t or "ORDINARIA" in t: return "GIALLA"
        return "VERDE"

    def is_salerno(self, comuni_list):
        """Verifica se la zona appartiene alla provincia di Salerno"""
        text = " ".join(comuni_list).upper()
        return any(c in text for c in self.provincia_salerno) or "(SA)" in text

    def is_cosenza(self, comuni_list):
        """Verifica se la zona appartiene alla provincia di Cosenza"""
        text = " ".join(comuni_list).upper()
        return any(c in text for c in self.provincia_cosenza) or "(CS)" in text

    def process(self):
        topo_url, filename = self.fetch_topo_json()
        if not topo_url: return

        print(f"📥 Download mappa: {topo_url.split('/')[-1]}")
        data = requests.get(topo_url).json()
        
        results = {"campania": [], "calabria": [], "basilicata": []}
        
        # Accesso alle geometrie del TopoJSON
        obj_key = list(data['objects'].keys())[0]
        geometries = data['objects'][obj_key]['geometries']

        for geo in geometries:
            p = geo.get("properties", {})
            nome_zona = p.get("Nome zona", "Senza Nome")
            comuni = p.get("Comuni", [])
            
            # Estrazione Rischio (Idrogeologico è il riferimento per la mappa)
            crit = self.get_alert_level(p.get("Rappresentata nella mappa", "Verde"))
            
            # 1. BASILICATA (Tutte le zone che iniziano con Basi-)
            if "BASI-" in nome_zona.upper():
                results["basilicata"].append({"zona": nome_zona.replace("Basi-", ""), "crit": crit})
            
            # 2. CAMPANIA (Filtro Salerno)
            elif self.is_salerno(comuni):
                results["campania"].append({"zona": nome_zona, "crit": crit})
                
            # 3. CALABRIA (Filtro Cosenza)
            elif self.is_cosenza(comuni):
                results["calabria"].append({"zona": nome_zona, "crit": crit})

        # Deduplicazione e pulizia
        for r in results:
            unique = {z['zona']: z['crit'] for z in results[r]}
            results[r] = [{"zona": k, "crit": v} for k, v in sorted(unique.items())]

        # Salvataggio dati per la mappa HTML
        results["metadata"] = {"update": datetime.now().strftime('%d/%m/%Y %H:%M'), "source": filename}
        with open("data_mappa.json", "w", encoding="utf-8") as j:
            json.dump(results, j, indent=4)
        
        self.generate_readme(results, filename)
        print(f"🚀 Fine. Salerno: {len(results['campania'])} | Cosenza: {len(results['calabria'])} | Basilicata: {len(results['basilicata'])}")

    def generate_readme(self, results, filename):
        report = f"# 🌩️ Monitoraggio Protezione Civile - Sud Italia\n\n"
        report += f"**Bollettino:** `{filename}` | **Aggiornamento:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        
        colors = {"VERDE": "🟢", "GIALLA": "🟡", "ARANCIONE": "🟠", "ROSSA": "🔴"}
        
        for reg in ["campania", "calabria", "basilicata"]:
            title = f"{reg.upper()} (Salerno)" if reg == "campania" else f"{reg.upper()} (Cosenza)" if reg == "calabria" else "BASILICATA"
            report += f"### 📍 {title}\n| Stato | Zona | Allerta |\n|---|---|---|\n"
            if not results[reg]:
                report += "| 🟢 | - | Nessuna allerta rilevata |\n"
            else:
                for item in results[reg]:
                    report += f"| {colors.get(item['crit'], '⚪')} | **{item['zona']}** | {item['crit']} |\n"
            report += "\n"
            
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(report)

if __name__ == "__main__":
    ProtezioneCivileSudAlert().process()
