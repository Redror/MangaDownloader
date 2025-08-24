import os
import zipfile
from PIL import Image

def criar_pdf_de_imagens(lista_imagens, pasta_base_imagens, caminho_pdf_saida):
    if os.path.exists(caminho_pdf_saida):
        print(f"  [⏩] PDF já existe, pulando: {os.path.basename(caminho_pdf_saida)}")
        return True

    imagens_para_pdf = []
    primeira_imagem = None

    for nome_arquivo in lista_imagens:
        img_path = os.path.join(pasta_base_imagens, nome_arquivo)
        try:
            # Abre todas as imagens com Pillow e converte para RGB para consistência
            img = Image.open(img_path).convert("RGB")
            if not primeira_imagem:
                primeira_imagem = img
            else:
                imagens_para_pdf.append(img)
        except Exception as e:
            print(f"  [x] Erro ao processar a imagem {nome_arquivo}: {e}")

    if not primeira_imagem:
        print("  [!] Nenhuma imagem válida encontrada para criar o PDF.")
        return False

    try:
        # Salva a primeira imagem, anexando as outras a ela
        primeira_imagem.save(
            caminho_pdf_saida, "PDF", resolution=100.0, save_all=True, append_images=imagens_para_pdf
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