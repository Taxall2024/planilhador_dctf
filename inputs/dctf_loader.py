def carregar_arquivos(arquivos):
    conteudos = []
    for arquivo in arquivos:
        conteudo = arquivo.read()
        nome = arquivo.name
        conteudos.append((nome, conteudo.decode("latin-1").splitlines()))
    return conteudos
