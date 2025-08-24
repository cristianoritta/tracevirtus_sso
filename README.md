# ALIAS TRACE SSO

Sistema de análise e investigação financeira.

## Máscaras de Formatação

### Máscara de Valores Monetários Brasileiros

A máscara `real` foi criada para formatar valores monetários no padrão brasileiro:

#### Uso no Template:
```html
{{ valor|real }}
```

#### Exemplos de Formatação:
- `1234.56` → `R$ 1.234,56`
- `1000000` → `R$ 1.000.000,00`
- `0` → `R$ 0,00`
- `None` → `R$ 0,00`
- `""` → `R$ 0,00`

#### Características:
- Formato brasileiro: R$ seguido do valor
- Separador de milhares: ponto (.)
- Separador decimal: vírgula (,)
- Sempre 2 casas decimais
- Tratamento robusto de valores nulos ou inválidos
- Suporte a diferentes formatos de entrada (com/sem separadores)

#### Implementação:
A máscara está implementada no arquivo `core/templatetags/mask.py` e pode ser usada em qualquer template do sistema.

### Máscara de Markdown

A máscara `markdown` foi criada para renderizar texto markdown em HTML:

#### Uso no Template:
```html
{{ texto|markdown }}
```

#### Exemplos de Formatação:
- `**texto**` → `<strong>texto</strong>`
- `*texto*` → `<em>texto</em>`
- `# Título` → `<h1>Título</h1>`
- `[link](url)` → `<a href="url">link</a>`
- `\`\`\`python\nprint("hello")\n\`\`\`` → Bloco de código Python

#### Características:
- Suporte a formatação básica (negrito, itálico, títulos)
- Suporte a links e imagens
- Suporte a blocos de código
- Suporte a tabelas
- Tratamento de erros robusto
- Fallback para texto original se markdown não estiver instalado

#### Dependências:
A biblioteca `markdown==3.7` foi adicionada ao `requirements.txt`.
