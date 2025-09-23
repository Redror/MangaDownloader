import os
import time
import re
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Mantenha as outras importações e a função baixar_capitulo_selenium como estão.
# Altere apenas a função obter_dados_obra_selenium.

def obter_dados_obra_selenium(obra_url, driver):
    """Abre a URL, extrai o HTML da lista de capítulos e o analisa para obter os dados."""
    print(f"Buscando informações da obra em: {obra_url}")
    try:
        driver.get(obra_url)
        driver.minimize_window()
        # 1. Espera pelo título e o extrai
        seletor_titulo = 'div.post-title h1'
        titulo_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_titulo))
        )
        obra_nome = titulo_element.text.strip()

        # 2. Espera pelo contêiner 'ul' que guarda a lista de capítulos
        seletor_container_caps = 'ul.version-chap'
        print("    -> Aguardando o contêiner da lista de capítulos...")
        container_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_container_caps))
        )
        
        html_do_container = container_element.get_attribute('innerHTML')

        regex_capitulos = r'<a href="([^"]+)">\s*([^<]+)\s*</a>'
        matches = re.findall(regex_capitulos, html_do_container)
        
        if not matches:
             print("!!! AVISO: Nenhum capítulo encontrado na análise do HTML. O layout pode ter mudado.")
             return obra_nome, []

        lista_de_capitulos = []
        for href, texto_link in matches:
            numero_capitulo_str = re.search(r'(\d+(\.\d+)?)', texto_link)
            if numero_capitulo_str:
                numero_capitulo = float(numero_capitulo_str.group(1))
                lista_de_capitulos.append({
                    'cap_numero': numero_capitulo, 
                    'cap_url': href
                })
        
        lista_de_capitulos.reverse()
        print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
        return obra_nome, lista_de_capitulos
        
    except Exception as e:
        print(f"Erro ao buscar informações da obra com Selenium: {e}")
        return None, None

def baixar_capitulo_selenium(chapter_info, driver, base_path):
    """Abre a URL de um capítulo do MangaLivre, aguarda o carregamento das imagens e as baixa."""
    chapter_url = chapter_info['cap_url']
    chapter_number = chapter_info['cap_numero']
    
    s_chapter_number = str(chapter_number)
    if '.' in s_chapter_number:
        parts = s_chapter_number.split('.')
        integer_part, fractional_part = parts[0], parts[1]
        if fractional_part == '0': formatted_number = integer_part.zfill(2)
        else: formatted_number = f"{integer_part.zfill(2)}.{fractional_part}"
    else: formatted_number = s_chapter_number.zfill(2)
    chapter_folder_name = f"Capítulo {formatted_number}"
    
    chapter_path = os.path.join(base_path, chapter_folder_name)
    os.makedirs(chapter_path, exist_ok=True)
    
    try:
        print(f"  Acessando página do capítulo {chapter_number}...")
        driver.get(chapter_url)
        seletor_imagens = 'div.chapter-images img.wp-manga-chapter-img'
        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_imagens)))
        time.sleep(2)
        paginas_elements = driver.find_elements(By.CSS_SELECTOR, seletor_imagens)
        
        if not paginas_elements:
            print(f"  Nenhuma imagem encontrada para o capítulo {chapter_number}.")
            return 0, 0
            
        print(f"  Encontradas {len(paginas_elements)} imagens. Baixando para '{chapter_folder_name}'...")
        images_downloaded = 0
        total_images = len(paginas_elements)
        
        session = requests.Session()
        session.headers.update({'Referer': chapter_url})
        
        for i, pagina_element in enumerate(paginas_elements):
            try:
                img_url = pagina_element.get_attribute('src')
                if not img_url: continue
                
                img_url = img_url.strip()
                _, extension = os.path.splitext(img_url.split('?')[0])
                if not extension: extension = '.jpg'
                filename = f"{str(i + 1).zfill(2)}{extension}"
                filepath = os.path.join(chapter_path, filename)
                
                img_response = session.get(img_url, stream=True)
                img_response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in img_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                images_downloaded += 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\n    -> Erro ao baixar a imagem {i+1} de '{img_url}': {e}")
        
        print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
        return images_downloaded, total_images - images_downloaded

    except Exception as e:
        print(f"  Ocorreu um erro geral ao processar o capítulo {chapter_number} com Selenium: {e}")
        return 0, 1
