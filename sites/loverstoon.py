import os
import time
import re
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def obter_dados_obra_loverstoon(obra_url, driver):
    """Abre a URL, clica em 'Show more' para carregar todos os capítulos e então extrai os dados."""
    print(f"Buscando informações da obra em: {obra_url}")
    try:
        driver.get(obra_url)
        
        # 1. Espera pelo título e o extrai
        seletor_titulo = 'div.post-title h1'
        titulo_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_titulo))
        )
        obra_nome = titulo_element.text.strip()
        print(f"    -> Título encontrado: '{obra_nome}'")
        driver.maximize_window()
        
        # 2. Rola a página para baixo até que o contêiner de capítulos seja encontrado
        seletor_container_caps = 'div.listing-chapters_wrap ul.version-chap'
        container_element = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_container_caps))
        )

        # 4. Lógica para clicar no botão 'Show more' específico dos capítulos (apenas uma vez)
        seletor_show_more_caps = 'span.chapter-readmore' 
        try:
            print("    -> Procurando por botão 'Show more' dos capítulos...")
            show_more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_show_more_caps))
            )
            driver.execute_script("arguments[0].click();", show_more_button)
            print("    -> Botão 'Show more' clicado para exibir todos os capítulos.")
            time.sleep(2)
        except TimeoutException:
            print("    -> Botão 'Show more' não encontrado, assumindo que todos os capítulos já estão visíveis.")
        except Exception as e:
            print(f"    -> Ocorreu um erro ao tentar clicar em 'Show more': {e}")

        # 5. Coleta a lista final de capítulos
        print("    -> Coletando a lista final de capítulos...")
        capitulos_elements = container_element.find_elements(By.CSS_SELECTOR, "li.wp-manga-chapter a")
        driver.minimize_window()
              
        if not capitulos_elements:
             print("!!! AVISO: Nenhum capítulo encontrado na análise. O layout pode ter mudado.")
             return obra_nome, []

        lista_de_capitulos = []
        for cap_element in capitulos_elements:
            href = cap_element.get_attribute('href')
            texto_link = cap_element.text
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
        return None, []

def download_image_with_session(driver, image_url, save_path):
    """Baixa a imagem usando a sessão de cookies do driver para evitar corrupção."""
    try:
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        session.headers.update({'Referer': driver.current_url})
        
        response = session.get(image_url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    -> Erro no download direto para '{image_url}': {e}")
        return False

def baixar_capitulo_loverstoon(chapter_info, driver, base_path):
    """Baixa um capítulo do Loverstoon."""
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

        print("    -> Procurando link para a página de imagens...")
        reading_content_link = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.reading-content a"))
        )
        image_page_url = reading_content_link.get_attribute('href')
        driver.get(image_page_url)

        seletor_container_imagens = 'div#player'
        print(f"    -> Aguardando container de imagens ...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_container_imagens))
        )
        time.sleep(2)

        seletor_imagens = f"{seletor_container_imagens} img"
        paginas_elements = driver.find_elements(By.CSS_SELECTOR, seletor_imagens)
        
        if not paginas_elements:
            print(f"  Nenhuma imagem encontrada para o capítulo {chapter_number}.")
            return 0, 0
            
        print(f"  Encontradas {len(paginas_elements)} imagens. Iniciando download...")
        
        images_downloaded = 0
        total_images = len(paginas_elements)
        
        for i, pagina_element in enumerate(paginas_elements):
            try:
                img_url = pagina_element.get_attribute('src')
                if not img_url or not img_url.strip():
                    print(f"\n    -> URL da imagem {i+1} está vazia. Pulando.")
                    continue
                
                img_url = img_url.strip()
                _, extension = os.path.splitext(img_url.split('?')[0])
                if not extension: extension = '.jpg'
                filename = f"{str(i + 1).zfill(2)}{extension}"
                filepath = os.path.join(chapter_path, filename)
                
                success = download_image_with_session(driver, img_url, filepath)
                if success:
                    images_downloaded += 1
                
                time.sleep(0.2)

            except Exception as e:
                print(f"\n    -> Erro no loop de download para a imagem {i+1} de '{img_url}': {e}")
        
        print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
        return images_downloaded, total_images - images_downloaded

    except Exception as e:
        print(f"  Ocorreu um erro geral ao processar o capítulo {chapter_number} com Selenium: {e}")
        return 0, 1