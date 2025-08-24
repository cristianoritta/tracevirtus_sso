import re
import unicodedata
from typing import Optional, List, Set


class NormalizadorNomes:
    """
    Classe para normalização de nomes de pessoas em português brasileiro.
    Trata preposições, conectivos, acentuação e formatação adequada.
    """
    
    # Palavras que devem permanecer em minúsculas (exceto no início)
    PREPOSICOES = {
        'de', 'da', 'do', 'das', 'dos', 'e', 'di', 'du',
        'del', 'de la', 'de las', 'de los', 'de lo',
        'van', 'von', 'vom', 'bin', 'le', 'la', 'los', 'las'
    }
    
    # Abreviações comuns que devem ser tratadas
    ABREVIACOES = {
        'jr', 'jr.', 'junior', 'júnior',
        'sr', 'sr.', 'senior', 'sênior',
        'neto', 'netto', 'filho', 'filha',
        'sobrinho', 'sobrinha', 'irmão', 'irmã'
    }
    
    # Títulos e pronomes de tratamento
    TITULOS = {
        'dr', 'dr.', 'dra', 'dra.', 'prof', 'prof.', 'profa', 'profa.',
        'sr', 'sr.', 'sra', 'sra.', 'srta', 'srta.',
        'eng', 'eng.', 'arq', 'arq.', 'adv', 'adv.',
        'pe', 'pe.', 'padre', 'frei', 'dom', 'dona',
        'me', 'me.', 'mestre', 'ms', 'ms.', 'phd', 'ph.d'
    }
    
    @staticmethod
    def remover_acentos(texto: str) -> str:
        """
        Remove acentos e caracteres especiais, mantendo apenas ASCII.
        
        Args:
            texto: String com possíveis acentos
            
        Returns:
            String sem acentos
        """
        # Normaliza para forma NFD e remove caracteres não-ASCII
        nfd = unicodedata.normalize('NFD', texto)
        sem_acento = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
        return sem_acento
    
    @staticmethod
    def limpar_espacos(texto: str) -> str:
        """
        Remove espaços múltiplos e espaços nas extremidades.
        
        Args:
            texto: String com possíveis espaços extras
            
        Returns:
            String com espaços normalizados
        """
        # Remove espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto)
        # Remove espaços nas extremidades
        return texto.strip()
    
    @staticmethod
    def capitalizar_palavra(palavra: str, is_primeira: bool = False) -> str:
        """
        Capitaliza uma palavra seguindo as regras do português.
        
        Args:
            palavra: Palavra a ser capitalizada
            is_primeira: Se é a primeira palavra do nome
            
        Returns:
            Palavra capitalizada adequadamente
        """
        palavra_lower = palavra.lower()
        
        # Se é uma preposição e não é a primeira palavra, mantém minúscula
        if not is_primeira and palavra_lower in NormalizadorNomes.PREPOSICOES:
            return palavra_lower
        
        # Trata casos especiais com apóstrofo (D'Angelo, O'Connor)
        if "'" in palavra:
            partes = palavra.split("'")
            return "'".join(p.capitalize() for p in partes)
        
        # Trata casos com hífen (Ana-Maria, João-Paulo)
        if "-" in palavra:
            partes = palavra.split("-")
            return "-".join(p.capitalize() for p in partes)
        
        # Capitalização normal
        return palavra.capitalize()
    
    @staticmethod
    def normalizar_nome(
        nome: str,
        remover_aspas: bool = True,
        remover_acentos: bool = False,
        remover_titulos: bool = False,
        manter_maiusculas: bool = False,
        formato: str = 'completo'
    ) -> str:
        """
        Normaliza um nome completo de pessoa.
        
        Args:
            nome: Nome a ser normalizado
            remover_acentos: Se True, remove acentos
            remover_titulos: Se True, remove títulos e pronomes de tratamento
            manter_maiusculas: Se True, mantém palavras totalmente maiúsculas
            formato: 'completo', 'primeiro_ultimo', 'iniciais', ou 'bibliografia'
            
        Returns:
            Nome normalizado
            
        Examples:
            >>> normalizar_nome("  JOÃO  DA  SILVA  ")
            'João da Silva'
            
            >>> normalizar_nome("maria josé DOS SANTOS", formato='primeiro_ultimo')
            'Maria Santos'
            
            >>> normalizar_nome("dr. PEDRO DE SOUZA FILHO", remover_titulos=True)
            'Pedro de Souza Filho'
            
            >>> normalizar_nome("Ana Maria da Silva", formato='bibliografia')
            'SILVA, Ana Maria da'
        """
        if not nome:
            return ""
        
        # Limpa espaços extras
        nome = NormalizadorNomes.limpar_espacos(nome)
        
        # Remove aspas se solicitado
        if remover_aspas:
            nome = nome.replace('"', "")
        
        # Remove acentos se solicitado
        if remover_acentos:
            nome = NormalizadorNomes.remover_acentos(nome)
        
        # Divide o nome em palavras
        palavras = nome.split()
        
        # Remove títulos se solicitado
        if remover_titulos:
            palavras = [p for p in palavras if p.lower().rstrip('.') not in NormalizadorNomes.TITULOS]
        
        # Capitaliza cada palavra adequadamente
        palavras_normalizadas = []
        for i, palavra in enumerate(palavras):
            # Se deve manter maiúsculas e a palavra está toda em maiúscula
            if manter_maiusculas and palavra.isupper() and len(palavra) > 2:
                palavras_normalizadas.append(palavra)
            else:
                palavras_normalizadas.append(
                    NormalizadorNomes.capitalizar_palavra(palavra, i == 0)
                )
        
        # Aplica o formato desejado
        if formato == 'primeiro_ultimo' and len(palavras_normalizadas) >= 2:
            return f"{palavras_normalizadas[0]} {palavras_normalizadas[-1]}"
        
        elif formato == 'iniciais':
            iniciais = [p[0].upper() + '.' for p in palavras_normalizadas 
                       if p.lower() not in NormalizadorNomes.PREPOSICOES]
            return ' '.join(iniciais)
        
        elif formato == 'bibliografia' and len(palavras_normalizadas) >= 2:
            # Formato: SOBRENOME, Nome
            ultimo = palavras_normalizadas[-1].upper()
            resto = ' '.join(palavras_normalizadas[:-1])
            return f"{ultimo}, {resto}"
        
        # Formato completo (padrão)
        return ' '.join(palavras_normalizadas)
    
    @staticmethod
    def comparar_nomes(nome1: str, nome2: str, threshold: float = 0.85) -> bool:
        """
        Compara dois nomes para verificar se são similares.
        
        Args:
            nome1: Primeiro nome
            nome2: Segundo nome
            threshold: Limite de similaridade (0 a 1)
            
        Returns:
            True se os nomes são similares
        """
        # Normaliza ambos os nomes removendo acentos
        n1 = NormalizadorNomes.normalizar_nome(nome1, remover_acentos=True).lower()
        n2 = NormalizadorNomes.normalizar_nome(nome2, remover_acentos=True).lower()
        
        # Comparação exata
        if n1 == n2:
            return True
        
        # Comparação por iniciais
        iniciais1 = NormalizadorNomes.normalizar_nome(nome1, formato='iniciais')
        iniciais2 = NormalizadorNomes.normalizar_nome(nome2, formato='iniciais')
        if iniciais1 == iniciais2:
            return True
        
        # Aqui você poderia adicionar algoritmos mais sofisticados como:
        # - Distância de Levenshtein
        # - Similaridade de Jaccard
        # - Soundex para português
        
        return False
    
    @staticmethod
    def extrair_primeiro_ultimo(nome: str) -> tuple:
        """
        Extrai o primeiro nome e sobrenome.
        
        Args:
            nome: Nome completo
            
        Returns:
            Tupla (primeiro_nome, sobrenome)
        """
        nome_normalizado = NormalizadorNomes.normalizar_nome(nome)
        palavras = nome_normalizado.split()
        
        if not palavras:
            return ("", "")
        elif len(palavras) == 1:
            return (palavras[0], "")
        else:
            # Ignora preposições no sobrenome
            for i in range(len(palavras)-1, 0, -1):
                if palavras[i].lower() not in NormalizadorNomes.PREPOSICOES:
                    return (palavras[0], palavras[i])
            return (palavras[0], palavras[-1])
    
    @staticmethod
    def validar_nome(nome: str) -> dict:
        """
        Valida um nome e retorna informações sobre ele.
        
        Args:
            nome: Nome a ser validado
            
        Returns:
            Dicionário com informações de validação
        """
        resultado = {
            'valido': True,
            'avisos': [],
            'nome_normalizado': '',
            'quantidade_palavras': 0,
            'tem_numeros': False,
            'tem_caracteres_especiais': False,
            'tem_titulo': False
        }
        
        if not nome or not nome.strip():
            resultado['valido'] = False
            resultado['avisos'].append('Nome vazio ou apenas espaços')
            return resultado
        
        nome_limpo = NormalizadorNomes.limpar_espacos(nome)
        palavras = nome_limpo.split()
        
        # Verifica quantidade de palavras
        resultado['quantidade_palavras'] = len(palavras)
        if len(palavras) < 2:
            resultado['avisos'].append('Nome pode estar incompleto (apenas uma palavra)')
        
        # Verifica números
        if re.search(r'\d', nome_limpo):
            resultado['tem_numeros'] = True
            resultado['avisos'].append('Nome contém números')
        
        # Verifica caracteres especiais (exceto acentos, hífen e apóstrofo)
        if re.search(r'[^a-zA-ZÀ-ÿ\s\'\-\.]', nome_limpo):
            resultado['tem_caracteres_especiais'] = True
            resultado['avisos'].append('Nome contém caracteres especiais incomuns')
        
        # Verifica títulos
        for palavra in palavras:
            if palavra.lower().rstrip('.') in NormalizadorNomes.TITULOS:
                resultado['tem_titulo'] = True
                resultado['avisos'].append(f'Nome contém título: {palavra}')
                break
        
        # Normaliza o nome
        resultado['nome_normalizado'] = NormalizadorNomes.normalizar_nome(nome_limpo)
        
        return resultado


# Função conveniente para uso direto
def normalizar_nome(
    nome: str,
    remover_acentos: bool = False,
    remover_titulos: bool = False,
    formato: str = 'completo'
) -> str:
    """
    Função conveniente para normalizar nomes.
    
    Args:
        nome: Nome a ser normalizado
        remover_acentos: Se True, remove acentos
        remover_titulos: Se True, remove títulos
        formato: 'completo', 'primeiro_ultimo', 'iniciais', ou 'bibliografia'
        
    Returns:
        Nome normalizado
        
    Examples:
        >>> normalizar_nome("  MARIA  DA  SILVA  ")
        'Maria da Silva'
        
        >>> normalizar_nome("joão carlos DOS SANTOS")
        'João Carlos dos Santos'
        
        >>> normalizar_nome("DR. PEDRO ÁLVARES CABRAL", remover_titulos=True)
        'Pedro Álvares Cabral'
    """
    return NormalizadorNomes.normalizar_nome(
        nome, 
        remover_acentos=remover_acentos,
        remover_titulos=remover_titulos,
        formato=formato
    )


# Exemplos de uso
if __name__ == "__main__":
    # Testes básicos
    nomes_teste = [
        "  JOÃO  DA  SILVA  ",
        "maria josé DOS SANTOS",
        "Dr. PEDRO ÁLVARES CABRAL",
        "Ana-Maria O'Connor da Silva",
        "JOSÉ DE SOUZA FILHO",
        "francisco d'angelo júnior",
        "Profª. Dra. MARIA HELENA VON SMITH",
        "luís gonzález de la rosa"
    ]
    
    print("=== NORMALIZAÇÃO BÁSICA ===")
    for nome in nomes_teste:
        print(f"Original: '{nome}'")
        print(f"Normalizado: '{normalizar_nome(nome)}'")
        print()
    
    print("=== DIFERENTES FORMATOS ===")
    nome_exemplo = "Dr. João Carlos da Silva Júnior"
    print(f"Original: {nome_exemplo}")
    print(f"Completo: {normalizar_nome(nome_exemplo)}")
    print(f"Sem título: {normalizar_nome(nome_exemplo, remover_titulos=True)}")
    print(f"Sem acentos: {normalizar_nome(nome_exemplo, remover_acentos=True)}")
    print(f"Primeiro/Último: {normalizar_nome(nome_exemplo, formato='primeiro_ultimo')}")
    print(f"Iniciais: {normalizar_nome(nome_exemplo, formato='iniciais')}")
    print(f"Bibliografia: {normalizar_nome(nome_exemplo, formato='bibliografia')}")
    print()
    
    print("=== VALIDAÇÃO ===")
    nome_validar = "Maria 123 da Silva @#"
    validacao = NormalizadorNomes.validar_nome(nome_validar)
    print(f"Nome: {nome_validar}")
    print(f"Validação: {validacao}")
    print()
    
    print("=== EXTRAÇÃO PRIMEIRO/ÚLTIMO ===")
    for nome in ["João Silva", "Maria de Souza", "Pedro", "Ana Clara dos Santos Lima"]:
        primeiro, ultimo = NormalizadorNomes.extrair_primeiro_ultimo(nome)
        print(f"{nome} -> Primeiro: '{primeiro}', Último: '{ultimo}'")