import os
import time
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from helpers import download_image_with_selenium

def obter_dados_obra_comick(obra_url, driver):
    """
    Obtém os dados da obra do site comick.io, com estratégia de espera robusta.
    """
    if "?lang" not in obra_url:
        obra_url += "?lang=pt-br"
    print(f"Buscando informações da obra em: {obra_url}")
    
    try:
        driver.get(obra_url)
        wait = WebDriverWait(driver, 30)

        lista_de_capitulos = []
        numeros_de_capitulo_vistos = set()
        
        # 1. ESPERAR PELO CONTÊINER PRINCIPAL DOS CAPÍTULOS PRIMEIRO
        print("    -> Aguardando o contêiner de capítulos carregar...")
        seletor_container = 'div[class*="2xl:min-w-6xl"]'
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_container)))
        print("      -> Contêiner de capítulos encontrado.")
        
        # 2. AGORA QUE O CONTÊINER EXISTE, PEGAR O TÍTULO
        seletor_titulo = 'div[class*="justify-between"] h1'
        titulo_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_titulo)))
        obra_nome = titulo_element.text.strip()
        print(f"    -> Título encontrado: '{obra_nome}'")

        page_num = 1
        while True:
            print(f"    -> Analisando a página de capítulos nº {page_num}...")
            try:
                # Garante que o contêiner ainda está visível antes de continuar
                container_element = driver.find_element(By.CSS_SELECTOR, seletor_container)
                time.sleep(2) 

                # 3. Encontrar os links DENTRO do contêiner
                capitulos_elements = container_element.find_elements(By.CSS_SELECTOR, "table tbody tr a")
                print(f"      -> {len(capitulos_elements)} links de capítulo encontrados nesta página.")

                if not capitulos_elements and page_num == 1:
                     print("!!! AVISO: Nenhum capítulo encontrado na primeira página. Verifique o idioma na URL.")
                     break
                elif not capitulos_elements:
                    break


                for cap_element in capitulos_elements:
                    try:
                        href = cap_element.get_attribute('href')
                        text = cap_element.text
                        if not href or not text:
                            continue

                        # Extrai o primeiro número encontrado no texto
                        num_match = re.search(r'(\d+(\.\d+)?)', text)
                        if num_match:
                            numero_capitulo = float(num_match.group(1))
                            if numero_capitulo not in numeros_de_capitulo_vistos:
                                numeros_de_capitulo_vistos.add(numero_capitulo)
                                lista_de_capitulos.append({
                                    'cap_numero': numero_capitulo,
                                    'cap_url': cap_element.get_attribute('href') # URL Relativa é suficiente
                                })
                    except Exception as e:
                        print(f"      -> Aviso: Erro ao processar um link de capítulo: {e}")

            except TimeoutException:
                print("    -> Tempo de espera esgotado ao procurar contêiner. Pode ser o fim da lista.")
                break
            except Exception as e:
                print(f"    -> Erro inesperado ao analisar a página: {e}")
                break

            # 4. Navegar para a próxima página
            try:
                pagina_atual = driver.find_element(By.CSS_SELECTOR, "a[aria-current='page']")
                proxima_pagina = pagina_atual.find_element(By.XPATH, "./following-sibling::a")
                
                print(f"    -> Indo para a próxima página ({proxima_pagina.text})...")
                driver.execute_script("arguments[0].click();", proxima_pagina)
                page_num += 1
            except Exception:
                print("    -> Não foi possível encontrar o botão da próxima página. Fim da lista.")
                break
        
        print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos únicos.")
        return obra_nome, lista_de_capitulos

    except Exception as e:
        print(f"!!! ERRO CRÍTICO ao buscar informações da obra no comick.io: {e}")
        return None, []


def baixar_capitulo_comick(chapter_info, driver, base_path):
    """
    Baixa um capítulo do comick.io, lidando com "Lazy Loading" através de scroll.
    """
    chapter_url = chapter_info['cap_url']
    # Adiciona o domínio aqui, no momento do acesso, se a URL for relativa
    if chapter_url.startswith('/'):
        chapter_url = f"https://comick.io{chapter_url}"

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
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='page']"))
        )
        time.sleep(3)

        print("    -> Rolando para carregar todas as imagens (lazy loading)...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("    -> Fim da página alcançado.")
                break
            last_height = new_height

        seletor_imagens = "div[id^='page'] img"
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
                
                success = download_image_with_selenium(driver, img_url, filepath)
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