import hashlib

# *******************************************
# MD5FILE
#   Calcula o hash MD5 de um arquivo
#
# *******************************************
def md5_file(fname):
    try:
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Erro ao calcular hash MD5 do arquivo {fname}: {e}")


# *******************************************
# SHA256
#   Calcula o hash SHA256 de um arquivo
#
# *******************************************
def sha256_file(file):
    sha256_hash = hashlib.sha256()
    try:
        # Ler o arquivo diretamente da requisição em chunks
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
        
        # Retornar o hash final em formato hexadecimal
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Erro ao calcular hash: {e}")
        return None


# Função para calcular o hash sha256 de um DataFrame pandas
def sha256_dataframe(df_string):
    # Inicializar o objeto hashlib para SHA-256
    sha256_hash = hashlib.sha256()
    
    # Atualizar o hash com a versão codificada da string (em bytes)
    sha256_hash.update(df_string.encode('utf-8'))
    
    # Retornar o hash final em formato hexadecimal
    return str(sha256_hash.hexdigest())