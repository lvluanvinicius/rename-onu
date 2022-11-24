from os import remove, rename
import unicodedata
import pandas as pd
from sys import argv


sessions_equipament = pd.read_json(f"{argv[1]}")


connections = pd.DataFrame(
    
    # Carregando arquivo.
    pd.read_csv("conexoes.csv", sep=";"),
    
    # Carregando apenas colunas selecionadas de acordo com a lista.
    columns=["Cód. Conexão", "Cliente", "Username", "Caixa NAP"]
).rename(
            
    # Renomeando as colunas selecionadas.
    columns={
    "Cód. Conexão": "COD_CONEXAO", "Cliente": "CLIENTE", "Username": "USERNAME", "Caixa NAP": "CAIXA_NAP"
})

radius = pd.DataFrame(
    # Carregando arquivo.
    pd.read_csv("radius.csv", sep=";", low_memory=False)
).rename(
    
    # Renomeando as colunas selecionadas.
    columns={
        "username": "USERNAME", "callingstationid": "MAC_SESSION"
    }
)

def get_sessions_active_in_equipament(data_file):
    auxPort=[]    
    for dmosBaseStatus in data_file["data"]:
        dmosShowPppoeSessionsPppoe = dmosBaseStatus["dmos-show-pppoe-sessions:pppoe"]\
            ["intermediate-agent"]["sessions"]["interface"]
        for i in dmosShowPppoeSessionsPppoe:
            for iface in dmosShowPppoeSessionsPppoe[i]:
                
                if not iface["number-of-sessions"] == "0":
                    # for sessInfo in iface["sessions-info"]:
                    auxPort.append({
                        f"{iface['interface']}": iface["sessions-info"]
                    })
                else: 
                    continue 
    return auxPort
                        

def get_client_in_mk_report_connections(data_file, username_pppoe):
    data_r=[]
    
    # Percorrendo todos os clientes.
    for clientsConnections in data_file.itertuples():
        
        if "float" in str(type(clientsConnections.USERNAME)): 
            continue

        if str(clientsConnections.USERNAME) == str(username_pppoe):
            data_r.append({
        	"COD_CONEXAO": clientsConnections.COD_CONEXAO,
        	"CLIENTE": clientsConnections.CLIENTE,
        	"USERNAME": clientsConnections.USERNAME,
            	"CAIXA_NAP": clientsConnections.CAIXA_NAP,
            })
            #clientsConnections
        
    return data_r


def get_sessions_in_mk_radius(data_file, mac_session):  
    
    for rdsLine in data_file.itertuples():        
        if rdsLine.MAC_SESSION == mac_session:
            return rdsLine
        else: 
            continue


rename_aux=[]
for port in get_sessions_active_in_equipament(data_file=sessions_equipament):
    # Percorrendo cadas porta do equipamento.
    for sessions in port:
        aux_port_client=[]
        
        # Percorrendo as sessoes de cada porta.
        for sess in port[sessions]:
            data_rad=get_sessions_in_mk_radius(data_file=radius, mac_session=sess['remote-mac'])
            
            if "NoneType" in str(type(data_rad)):
                continue
            

            client_data=get_client_in_mk_report_connections(data_file=connections, username_pppoe=str(data_rad.USERNAME))
            
            client={}
            for cli in client_data:
                client=cli               
            
            if len(client) == 0:
                continue
            
            else:
                # Transformando em string
                name = str(client['CLIENTE'])
                
                # Removendo acentos.
                name_no_accents = string_nova = ''.join(ch for ch in unicodedata.normalize('NFKD', name) \
                    if not unicodedata.combining(ch))
                             
                # Carregando e transformando em lista o nome de cada NAP.
                textCX=client['CAIXA_NAP'].split("_")
                cx_for_name=""
                
                # Verificando tipo de caixa e adequando cada uma com seu tipo.
                if len(textCX) == 3:                                            
                    cx_for_name=textCX[1] + textCX[-1]
                
                elif len(textCX) == 5:                                            
                    cx_for_name=textCX[1] + textCX[-1]
                
                elif len(textCX) == 4 and "RURAL" in textCX:
                    cx_for_name=textCX[1] + textCX[-1]
                    
                elif len(textCX) == 4 and "CTO" in textCX:
                    cx_for_name=textCX[2] + textCX[-1] + "_" + textCX[1]
                    print(cx_for_name)
                
                # Criando nomenclatura.
                new_name=f"{cx_for_name}-{client['COD_CONEXAO']}-{name_no_accents.strip().replace(' ', '_')}"
                if new_name[0] == "-":
                    new_name=new_name[1:]
                
                
                # Verificando se o nome possui mais que 48 caracteres.
                if len(new_name) > 48:
                    # Buscando a quantidade de caracter que passou na string.
                    removeNumberCaracter = (len(new_name)-48)
                    
                    # Removendo a quantidade de caracteres que passou de 48.
                    new_name=new_name[:-removeNumberCaracter]
                    
                
                # Criando objeto com os dados dos clientes a serem utilzados no rename.
                aux_port_client.append({
                    "NAME_ONU": new_name,
                    "ONU_ID": sess["onu-id"]
                })
                                                
        rename_aux.append({
            "GPON": sessions,
            "CLIENTS": aux_port_client
        })




# Mensagem de resposta certa: Validation complete


commands=["config"]
for gp in rename_aux:
    commands.append(f"interface gpon {gp['GPON']}")
    for clItem in gp['CLIENTS']:         
        commands.append(f"onu {str(clItem['ONU_ID'])}")
        commands.append(f"name {str(clItem['NAME_ONU'])}")
    
    commands.append("top")
    commands.append("commit check")
    commands.append("="*10+f"{gp['GPON']}"+"="*100)
    

with open(f"{argv[1][:-5]}.commands.txt", 'w') as cmd:
     for line in commands:
         cmd.writelines(line + "\n")

     cmd.close()
