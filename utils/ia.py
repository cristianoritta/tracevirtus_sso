import os
import random
import json
import re
from openai import OpenAI


def executar_prompt(prompt):
    """
    Executa um prompt usando o modelo especificado da OpenAI e retorna o texto da resposta.

    Args:
        prompt (str): O texto do prompt a ser enviado para a IA
        modelo (str): O nome do modelo a ser usado (padrão: 'gpt-3.5-turbo')

    Returns:
        str: O texto da resposta gerada pela IA
    """

    api_key = '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'
    api_key = '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'
    base_url = 'https://api.groq.com/openai/v1'
    modelo = 'meta-llama/llama-4-scout-17b-16e-instruct'

    if not api_key:
        return "Erro: A chave da API não está configurada."

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        chat_completion = client.chat.completions.create(
            #
            # Required parameters
            #
            messages=prompt,

            # The language model which will generate the completion.
            model=modelo,

            #
            # Optional parameters
            #

            # Controls randomness: lowering results in less random completions.
            # As the temperature approaches zero, the model will become deterministic
            # and repetitive.
            temperature=0.5,

            # The maximum number of tokens to generate. Requests can use up to
            # 32,768 tokens shared between prompt and completion.
            max_tokens=4096,

            # Controls diversity via nucleus sampling: 0.5 means half of all
            # likelihood-weighted options are considered.
            top_p=1,

            # A stop sequence is a predefined or user-specified text string that
            # signals an AI to stop generating content, ensuring its responses
            # remain focused and concise. Examples include punctuation marks and
            # markers like "[end]".
            stop=None,

            # If set, partial message deltas will be sent.
            stream=False,
        )

        # Print the completion returned by the LLM.
        resumo = chat_completion.choices[0].message.content
    except Exception as e:
        print("ERRO AO EXECUTAR_IA", e)
        resumo = None

    return resumo
