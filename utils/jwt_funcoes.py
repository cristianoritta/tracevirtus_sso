import jwt
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError, DecodeError

def carregar_chave_privada(caminho: str = "keys/private.pem"):
    """
    Carrega a chave privada RSA de um arquivo PEM
    Retorna a chave privada ou levanta exceção
    """
    try:
        with open(caminho, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    except Exception as e:
        raise RuntimeError(f"Falha ao carregar chave privada: {str(e)}") from e

def carregar_chave_publica(caminho: str = "keys/public.pem"):
    """
    Carrega a chave pública RSA de um arquivo PEM
    Retorna a chave pública ou levanta exceção
    """
    try:
        with open(caminho, "rb") as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    except Exception as e:
        raise RuntimeError(f"Falha ao carregar chave pública: {str(e)}") from e

def gerar_jwt(private_key, payload: dict = None):
    """
    Gera um token JWT assinado com RS256
    Retorna o token ou levanta exceção
    """
    try:
        # Payload padrão se não for fornecido
        if not payload:
            payload = {
                "user_id": 1,
                "username": "alvaro",
                "email": "alvarolucasno@gmail.com",
                "exp": int(time.time()) + 3600,  # 1 hora
                "apps": ["MTK", "ALIAS RECON"],
                "scope": "read write",
                "nome_completo": ""
            }
        
        return jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"typ": "JWT", "alg": "RS256"}
        )
    
    except Exception as e:
        raise RuntimeError(f"Falha na geração do JWT: {str(e)}") from e

def ler_jwt(token, public_key, verificar_exp: bool = True, verificar_assinatura: bool = True):
    """
    Verifica e decodifica um token JWT
    Retorna o payload ou levanta exceção
    """
    try:
        print(token)
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": verificar_assinatura,
                "verify_exp": verificar_exp
            }
        )
    except InvalidSignatureError as e:
        raise ValueError("Assinatura inválida") from e
    except ExpiredSignatureError as e:
        raise ValueError("Token expirado") from e
    except DecodeError as e:
        raise ValueError("Token inválido") from e
    except Exception as e:
        raise RuntimeError(f"Erro na decodificação: {str(e)}") from e

if __name__ == "__main__":
    try:
        # 1. Carregar chaves
        privada = carregar_chave_privada()
        publica = carregar_chave_publica()
        
        # 2. Gerar token
        token = gerar_jwt(privada)
        print("Token JWT gerado:")
        print(token)
        print("\n" + "-"*50 + "\n")
        
        # 3. Verificar token
        payload = ler_jwt(token, publica)
        print("Token verificado com sucesso! Conteúdo:")
        for chave, valor in payload.items():
            print(f"{chave}: {valor}")
            
        # 4. Verificar compatibilidade das chaves
        print("\n" + "-"*50)
        if publica.public_numbers() == privada.public_key().public_numbers():
            print("✅ Chaves pública e privada são compatíveis")
        else:
            print("❌ As chaves não correspondem!")
            
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        if isinstance(e, (ValueError, RuntimeError)):
            print(f"Detalhes: {e.__cause__}")