import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

def dividir_mensagem(mensagem: str, tamanho_maximo: int = 3000) -> list:
    """
    Divide uma mensagem longa em partes menores.
    
    Args:
        mensagem (str): A mensagem a ser dividida.
        tamanho_maximo (int): Tamanho máximo de cada parte (padrão: 3000).
        
    Returns:
        list: Lista contendo as partes da mensagem.
    """
    tamanho_efetivo = tamanho_maximo - 20
    blocos = mensagem.split('\n\n')
    partes = []
    parte_atual = ""
    
    for bloco in blocos:
        if len(bloco) > tamanho_efetivo:
            if parte_atual:
                partes.append(parte_atual)
                parte_atual = ""
            
            linhas = bloco.split('\n')
            linha_atual = ""
            
            for linha in linhas:
                if len(linha) > tamanho_efetivo:
                    if linha_atual:
                        partes.append(linha_atual)
                        linha_atual = ""
                    
                    for i in range(0, len(linha), tamanho_efetivo):
                        partes.append(linha[i:i + tamanho_efetivo])
                elif len(linha_atual) + len(linha) + (1 if linha_atual else 0) > tamanho_efetivo:
                    partes.append(linha_atual)
                    linha_atual = linha
                else:
                    if linha_atual:
                        linha_atual += '\n' + linha
                    else:
                        linha_atual = linha
            
            if linha_atual:
                partes.append(linha_atual)
        
        elif len(parte_atual) + len(bloco) + (2 if parte_atual else 0) > tamanho_efetivo:
            partes.append(parte_atual)
            parte_atual = bloco
        else:
            if parte_atual:
                parte_atual += '\n\n' + bloco
            else:
                parte_atual = bloco
    
    if parte_atual:
        partes.append(parte_atual)
    
    return partes

def enviar_mensagem(mensagem: str, id_telegram: str) -> bool:
    """
    Função para enviar mensagem para o grupo do Telegram usando requests.
    Suporta divisão automática de mensagens longas.

    Args:
        mensagem (str): O texto da mensagem a ser enviada.
        id_telegram (str): ID do chat/grupo do Telegram.

    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário.
    """
    TOKEN_BOT = os.getenv('TELEGRAM_TOKEN')

    try:
        partes = dividir_mensagem(mensagem)
        total_partes = len(partes)
        
        for i, parte in enumerate(partes, 1):
            texto = f"[Parte {i}/{total_partes}]\n\n{parte}" if total_partes > 1 else parte
            
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
            params = {
                "chat_id": id_telegram,
                "text": texto
            }

            response = requests.post(url, data=params)

            if response.status_code != 200:
                print(f"Falha ao enviar parte {i}/{total_partes}. Status code: {response.status_code}, Resposta: {response.text}")
                return False
                
            if i < total_partes:
                time.sleep(1)  # Aguarda 1 segundo entre mensagens para evitar flood

        print(f"Mensagem enviada com sucesso para o chat {id_telegram}")
        return True

    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")
        return False

def notificar_grupo(mensagem: str) -> bool:
    """
    Envia uma mensagem para o grupo configurado no ambiente.
    
    Args:
        mensagem (str): A mensagem a ser enviada.
        
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário.
    """
    GRUPO_ID = os.getenv('TELEGRAM_CHAT_ID')
    return enviar_mensagem(mensagem, GRUPO_ID)

if __name__ == "__main__":
    notificar_grupo("Teste ALIAS RECON.")

