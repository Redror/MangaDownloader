import os
import time
import re
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Variável para controlar o estado do popup de termos
SUSSY_TERMS_ACCEPTED = False

def obter_dados_obra_sussy_api(obra_url, scraper_session):
    """Obtém a lista de capítulos do SussyToons via API, incluindo status de disponibilidade."""
    print(f"Buscando lista de capítulos via API para: {obra_url}")
    try:
        obra_id = re.search(r'/obra/(\d+)', obra_url).group(1)
        api_url = f"https://api.sussytoons.wtf/obras/{obra_id}"
        response = scraper_session.get(api_url)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            resultado = data['resultado']
            obra_nome = resultado.get('obr_nome', f"obra_{obra_id}")
            capitulos_api = resultado.get('capitulos', [])
            
            lista_de_capitulos = []
            for cap in capitulos_api:
                # Constrói a URL do capítulo usando o formato correto com cap_id
                cap_url = f"https://www.sussytoons.wtf/capitulo/{cap['cap_id']}"
                lista_de_capitulos.append({
                    'cap_numero': float(cap['cap_numero']),
                    'cap_url': cap_url,
                    'cap_disponivel': cap.get('cap_disponivel', True), # Assume disponível se a chave não existir
                    'obra_id': obra_id
                })

            lista_de_capitulos.reverse()
            print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
            return obra_nome, lista_de_capitulos
        return None, None
    except Exception as e:
        print(f"Erro ao buscar informações da obra via API: {e}")
        return None, None

def baixar_capitulo_sussy_bloqueado(chapter_info, scraper_session, base_path):
    """Tenta baixar as imagens de um capítulo bloqueado do SussyToons adivinhando as URLs."""
    chapter_number = chapter_info['cap_numero']
    obra_id = chapter_info['obra_id']
    
    print("-> Este é um capítulo bloqueado. Tentando adquirir as páginas diretamente...")
    
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
    
    images_downloaded = 0
    total_images = 0 # Não sabemos o total, então contamos enquanto baixamos

    # Formata o número do capítulo para a URL (substitui '.' por '_')
    chapter_url_part = str(chapter_number).replace('.', '_')
    
    base_url = f"https://cdn.sussytoons.site/scans/1/obras/{obra_id}/capitulos/{chapter_url_part}/"
    
    # Ordem de tentativa dos formatos
    formats = ["{:02d}.jpg", "{:02d}-optimized.jpg", "{:02d}.webp"]
    
    page_index = 0
    active_format = None

    while True:
        image_found_for_index = False
        
        if active_format:
            # Se já encontramos um formato, tentamos ele primeiro para a próxima página
            try:
                page_filename = active_format.format(page_index)
                img_url = base_url + page_filename
                response = scraper_session.get(img_url, stream=True, timeout=5)
                if response.status_code == 200:
                    filepath = os.path.join(chapter_path, f"{str(page_index).zfill(2)}{os.path.splitext(page_filename)[1]}")
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    images_downloaded += 1
                    image_found_for_index = True
                else:
                    # Se o formato ativo falhou, significa que o capítulo acabou
                    break
            except requests.exceptions.RequestException:
                break # Sai do loop se houver erro de conexão
        else:
            # Se ainda não temos um formato ativo, testamos todos
            for fmt in formats:
                try:
                    page_filename = fmt.format(page_index)
                    img_url = base_url + page_filename
                    response = scraper_session.get(img_url, stream=True, timeout=5)
                    if response.status_code == 200:
                        active_format = fmt # Define o formato ativo para as próximas páginas
                        filepath = os.path.join(chapter_path, f"{str(page_index).zfill(2)}{os.path.splitext(page_filename)[1]}")
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        images_downloaded += 1
                        image_found_for_index = True
                        break # Sai do loop de formatos e vai para a próxima página
                except requests.exceptions.RequestException:
                    continue # Tenta o próximo formato

        if not image_found_for_index:
            # Se nenhuma imagem foi encontrada para o índice atual, paramos
            break
            
        page_index += 1

    total_images = images_downloaded # O total é o que conseguimos baixar
    print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
    return images_downloaded, 0 # Retorna 0 falhas pois não sabemos o total real

def baixar_capitulo_sussy_selenium(chapter_info, driver, base_path):
    """Navega para a página de um capítulo do SussyToons com Selenium e baixa as imagens."""
    global SUSSY_TERMS_ACCEPTED
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
        wait = WebDriverWait(driver, 20)

        # Lida com o popup de termos de uso, apenas uma vez
        if not SUSSY_TERMS_ACCEPTED:
            try:
                print("    -> Procurando por popup de termos...")
                accept_button_selector = "//button[text()='Aceito os Termos']"
                accept_button = wait.until(EC.element_to_be_clickable((By.XPATH, accept_button_selector)))
                accept_button.click()
                print("      -> Popup de termos aceito.")
                SUSSY_TERMS_ACCEPTED = True
                time.sleep(2)
            except Exception:
                print("    -> Nenhum popup de termos encontrado, continuando...")
                SUSSY_TERMS_ACCEPTED = True # Assume que não aparecerá mais
        
        seletor_imagens = 'div.css-21onc5 img.css-8atqhb'
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_imagens)))
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
                
                img_response = session.get(img_url, stream=True, timeout=20)
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