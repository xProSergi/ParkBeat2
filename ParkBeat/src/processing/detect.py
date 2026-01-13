import pandas as pd

# Cargar CSV (si lo tienes como archivo)
# df = pd.read_csv("ruta_del_csv.csv")

# O si ya lo tienes como texto, puedes usar StringIO
from io import StringIO

data = """zona,atraccion,tiempo_espera,abierta,ultima_actualizacion,fecha,hora,dia_semana,timestamp,mes,fin_de_semana,temperatura,humedad,sensacion_termica,codigo_clima
Cartoon Village,A Toda Máquina,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Academia de Pilotos Baby Looney Tunes,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Cartoon Carousel,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Convoy de Camiones,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Correcaminos Bip Bip,15,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Emergencias Pato Lucas,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Escuela de Conducción Yabba-Dabba-Doo,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,He Visto un Lindo Gatito,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,La Aventura de Scooby-Doo,20,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,La Captura de Gossamer,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Looney Tunes Correo Aéreo,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Marvin el Marciano Cohetes Espaciales,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Pato Lucas Coches Locos,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Piolín y Silvestre Paseo en Autobús,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Rápidos ACME,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Scooby-Doo's Tea Party Mistery,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Tom & Jerry Picnic en el Parque,10,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,Wile E. Coyote Zona de Explosión,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,Batman Gotham City Escape,20,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,La Venganza del Enigma,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,Lex Luthor Invertatron,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,Mr. Freeze Fábrica de Hielo,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,Shadows of Arkham,15,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,Superman La Atracción de Acero,10,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
DC Super Heroes World,The Joker Coches de Choque,10,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Movie World Studios,Cine Tour,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Movie World Studios,Hotel Embrujado,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Movie World Studios,Oso Yogui,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Movie World Studios,Stunt Fall,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Old West Territory,Cataratas Salvajes,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Old West Territory,Coaster Express,20,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Old West Territory,Los Carros de la Mina,5,True,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Old West Territory,Río Bravo,0,False,2025-10-30 15:25:08+00:00,2025-10-30,16:26:19,Thursday,2025-10-30 16:26:19,October,False,17.6,68,16.4,2
Cartoon Village,A Toda Máquina,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Academia de Pilotos Baby Looney Tunes,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Cartoon Carousel,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Convoy de Camiones,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Correcaminos Bip Bip,10,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Emergencias Pato Lucas,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Escuela de Conducción Yabba-Dabba-Doo,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,He Visto un Lindo Gatito,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,La Aventura de Scooby-Doo,999,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,La Captura de Gossamer,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Looney Tunes Correo Aéreo,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Marvin el Marciano Cohetes Espaciales,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Pato Lucas Coches Locos,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Piolín y Silvestre Paseo en Autobús,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Rápidos ACME,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Scooby-Doo's Tea Party Mistery,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Tom & Jerry Picnic en el Parque,10,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,Wile E. Coyote Zona de Explosión,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Batman Gotham City Escape,15,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,La Venganza del Enigma,10,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Lex Luthor Invertatron,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Mr. Freeze Fábrica de Hielo,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Shadows of Arkham,15,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Superman La Atracción de Acero,10,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
DC Super Heroes World,The Joker Coches de Choque,10,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Movie World Studios,Cine Tour,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Movie World Studios,Hotel Embrujado,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Movie World Studios,Oso Yogui,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Movie World Studios,Stunt Fall,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Old West Territory,Cataratas Salvajes,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Old West Territory,Coaster Express,30,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Old West Territory,Los Carros de la Mina,5,True,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Old West Territory,Río Bravo,0,False,2025-10-30 15:40:09+00:00,2025-10-30,16:41:20,Thursday,2025-10-30 16:41:20,October,False,17.6,68,16.4,2
Cartoon Village,A Toda Máquina,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Academia de Pilotos Baby Looney Tunes,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Cartoon Carousel,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Convoy de Camiones,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Correcaminos Bip Bip,20,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Emergencias Pato Lucas,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Escuela de Conducción Yabba-Dabba-Doo,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,He Visto un Lindo Gatito,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,La Aventura de Scooby-Doo,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,La Captura de Gossamer,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Looney Tunes Correo Aéreo,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Marvin el Marciano Cohetes Espaciales,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Pato Lucas Coches Locos,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Piolín y Silvestre Paseo en Autobús,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Rápidos ACME,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Scooby-Doo's Tea Party Mistery,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Tom & Jerry Picnic en el Parque,10,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,Wile E. Coyote Zona de Explosión,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Batman Gotham City Escape,10,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,La Venganza del Enigma,20,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Lex Luthor Invertatron,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Mr. Freeze Fábrica de Hielo,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Shadows of Arkham,15,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,Superman La Atracción de Acero,15,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
DC Super Heroes World,The Joker Coches de Choque,10,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Movie World Studios,Cine Tour,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Movie World Studios,Hotel Embrujado,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Movie World Studios,Oso Yogui,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Movie World Studios,Stunt Fall,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Old West Territory,Cataratas Salvajes,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Old West Territory,Coaster Express,20,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Old West Territory,Los Carros de la Mina,5,True,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Old West Territory,Río Bravo,0,False,2025-10-30 15:55:09+00:00,2025-10-30,16:56:20,Thursday,2025-10-30 16:56:20,October,False,17.6,68,16.4,2
Cartoon Village,A Toda Máquina,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Academia de Pilotos Baby Looney Tunes,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Cartoon Carousel,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Convoy de Camiones,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Correcaminos Bip Bip,20,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Emergencias Pato Lucas,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Escuela de Conducción Yabba-Dabba-Doo,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,He Visto un Lindo Gatito,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,La Aventura de Scooby-Doo,10,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,La Captura de Gossamer,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Looney Tunes Correo Aéreo,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Marvin el Marciano Cohetes Espaciales,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Pato Lucas Coches Locos,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Piolín y Silvestre Paseo en Autobús,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Rápidos ACME,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Scooby-Doo's Tea Party Mistery,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Tom & Jerry Picnic en el Parque,10,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Cartoon Village,Wile E. Coyote Zona de Explosión,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,Batman Gotham City Escape,15,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,La Venganza del Enigma,20,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,Lex Luthor Invertatron,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,Mr. Freeze Fábrica de Hielo,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,Shadows of Arkham,15,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,Superman La Atracción de Acero,25,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
DC Super Heroes World,The Joker Coches de Choque,10,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Movie World Studios,Cine Tour,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Movie World Studios,Hotel Embrujado,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Movie World Studios,Oso Yogui,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Movie World Studios,Stunt Fall,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Old West Territory,Cataratas Salvajes,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Old West Territory,Coaster Express,20,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Old West Territory,Los Carros de la Mina,5,True,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
Old West Territory,Río Bravo,0,False,2025-10-30 16:10:09+00:00,2025-10-30,17:11:20,Thursday,2025-10-30 17:11:20,October,False,17.4,69,16.2,1
"""
df = pd.read_csv(StringIO(data))

# Seleccionamos la columna numérica
columna = 'tiempo_espera'

# Calcular Q1, Q3 e IQR
Q1 = df[columna].quantile(0.25)
Q3 = df[columna].quantile(0.75)
IQR = Q3 - Q1

# Definir límites
limite_inferior = Q1 - 1.5 * IQR
limite_superior = Q3 + 1.5 * IQR

# Filtrar outliers
outliers = df[(df[columna] < limite_inferior) | (df[columna] > limite_superior)]

print("Valores atípicos detectados:")
print(outliers[['zona','atraccion','tiempo_espera']])
