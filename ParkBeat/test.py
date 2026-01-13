from datetime import datetime, time
from bs4 import BeautifulSoup
from requests import request
import json

HORA_INICIO = '12:00:00'
HORA_FIN    = '19:30:00'

def hora_valida(data) -> bool:
    try:
        dt = datetime.strptime(data[0], "%d/%m/%y %H:%M:%S")
        
        h_inicio = datetime.strptime(HORA_INICIO, "%H:%M:%S")
        h_fin = datetime.strptime(HORA_FIN, "%H:%M:%S")
    
        return h_inicio.time() <= dt.time() <= h_fin.time()
    except ValueError:
        return False

res = request('GET', 'https://queue-times.com/parks/298/rides/8844?given_date=2025-11-09#day')

soup = BeautifulSoup(res.text)

for script in soup.html.body.find_all('script'):
    if "createChart" in script.text:
        if '"chart-1"' in script.text:
            segment = script.text.split(f'"chart-1", ')[1].split(f', {{"colors"')[0]
            stats = json.loads(segment)

            for stat in stats:
                statName = stat['name']
                statData = stat['data']

                statData = list(filter(hora_valida, statData))

                print(f"{statName}: {len(statData)}")
            
        elif "chart-2" in script.text:
            pass

