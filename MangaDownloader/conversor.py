import os
import zipfile
from PIL import Image

def criar_pdf_de_imagens(lista_imagens, pasta_base_imagens, caminho_pdf_saida):
    if os.path.exists(caminho_pdf_saida):
        print(f"  [⏩] PDF já existe, pulando: {os.path.basename(caminho_pdf_saida)}")
        return True

    imagens_processadas = []
    largura_padrao = 0

    # Primeiro, abre a primeira imagem para definir a largura padrão para todas as páginas
    if lista_imagens:
        try:
            primeira_img_path = os.path.join(pasta_base_imagens, lista_imagens[0])
            with Image.open(primeira_img_path) as img:
                largura_padrao = img.width
        except Exception as e:
            print(f"  [x] Erro ao ler a primeira imagem para definir o padrão: {e}")
            return False

    if largura_padrao == 0:
        print("  [!] Não foi possível definir uma largura padrão para o PDF.")
        return False

    # Processa todas as imagens da lista
    for nome_arquivo in lista_imagens:
        img_path = os.path.join(pasta_base_imagens, nome_arquivo)
        try:
            # Abre a imagem e converte para RGB para consistência
            img = Image.open(img_path).convert("RGB")
            
            # Se a largura da imagem for diferente da padrão, redimensiona
            if img.width != largura_padrao:
                # Calcula a nova altura para manter a proporção
                altura_proporcional = int((largura_padrao / float(img.width)) * img.height)
                img = img.resize((largura_padrao, altura_proporcional), Image.Resampling.LANCZOS)
            
            imagens_processadas.append(img)
        except Exception as e:
            print(f"  [x] Erro ao processar a imagem {nome_arquivo}: {e}")

    if not imagens_processadas:
        print("  [!] Nenhuma imagem válida encontrada para criar o PDF.")
        return False

    try:
        # A primeira imagem da lista processada será a base, e as outras serão anexadas
        primeira_imagem = imagens_processadas[0]
        imagens_restantes = imagens_processadas[1:]
        
        primeira_imagem.save(
            caminho_pdf_saida, "PDF", resolution=100.0, save_all=True, append_images=imagens_restantes
        )
        print(f"  [✔] PDF criado com sucesso: {os.path.basename(caminho_pdf_saida)}")
        return True
    except Exception as e:
        print(f"  [x] Erro ao salvar o PDF final: {e}")
        return False


def criar_cbz_de_imagens(lista_imagens, pasta_base_imagens, caminho_cbz_saida):
    if os.path.exists(caminho_cbz_saida):
        print(f"  [⏩] CBZ já existe, pulando: {os.path.basename(caminho_cbz_saida)}")
        return True
    try:
        with zipfile.ZipFile(caminho_cbz_saida, 'w', zipfile.ZIP_DEFLATED) as zf:
            for nome_arquivo in lista_imagens:
                caminho_completo = os.path.join(pasta_base_imagens, nome_arquivo)
                zf.write(caminho_completo, arcname=nome_arquivo)
        print(f"  [✔] CBZ criado com sucesso: {os.path.basename(caminho_cbz_saida)}")
        return True
    except Exception as e:
        print(f"  [x] Erro ao criar o arquivo CBZ {os.path.basename(caminho_cbz_saida)}: {e}")
        return False