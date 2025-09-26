import requests
import json
import re

LLM_URL = "http://localhost:8080/api/llm/query"

def get_tags_from_llm(plat_text):
    prompt = f"""
    Ets un expert en gastronomia. Analitza el següent plat i genera tags i ingredients.
    Retorna JSON amb "tags" i "ingredients".
    Plat: "{plat_text}"
    """
    resp = requests.post(LLM_URL, json={"prompt": prompt}, timeout=10)
    if resp.status_code != 200:
        return [], []
    
    answer = resp.json().get("answer", "")
    m = re.search(r'\{.*\}', answer, re.DOTALL)
    if not m:
        return [], []
    data = json.loads(m.group(0))
    return data.get("tags", []), data.get("ingredients", [])

def get_normalized_name(name):
    prompt = f"""
    Ets un expert en gastronomia. Normalitza el nom del següent plat, en un sol idioma (català).
    Per tant treu paraules innecessàries, duplicats, cadenes en altres idiomes,...
    No canvis el significat del plat. I sobretot revisa que al traduir no es perdi ni afegeixi res.
    Torna'm nomes el nom normalitzat.
    Plat: "{name}"
    """
    resp = requests.post(LLM_URL, json={"prompt": prompt}, timeout=10)
    if resp.status_code != 200:
        return [], []
    
    answer = resp.json().get("answer", "")
    return answer.strip()