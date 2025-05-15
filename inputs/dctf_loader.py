def carregar_arquivos(lista_arquivos):
    conteudos = []
    for arquivo in lista_arquivos:
        nome = getattr(arquivo, 'name', 'arquivo')
        linhas = [linha.decode('latin1').rstrip('\r\n') for linha in arquivo.readlines()]
        conteudos.append((nome, linhas))
    return conteudos
