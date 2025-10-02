import os
import re
import time
from urllib.parse import urljoin

# Imports do Selenium, que já estão no seu projeto
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Importa a função de download que usa a sessão do Selenium, que é mais robusta
from sites.manhastro import download_image_with_session


def obter_dados_obra_batoto(obra_url, driver):
    """
    Obtém os dados da obra do Batoto usando Selenium para garantir que a página carregue.
    """
    print(f"Buscando informações da obra em: {obra_url}")
    try:
        driver.get(obra_url)
        wait = WebDriverWait(driver, 20)

        # Espera o título ficar visível
        titulo_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "h3.item-title a"))
        )
        obra_nome = titulo_element.text.strip()

        # Espera a lista de capítulos carregar
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.visited.chapt"))
        )
        capitulos_elements = driver.find_elements(By.CSS_SELECTOR, "a.visited.chapt")
        
        if not capitulos_elements:
            print("!!! AVISO: Nenhum link de capítulo encontrado.")
            return obra_nome, []

        lista_de_capitulos = []
        for cap_element in capitulos_elements:
            href_relativo = cap_element.get_attribute("href")
            if not href_relativo:
                continue
            
            cap_url_completa = urljoin(obra_url, href_relativo)
            cap_text = cap_element.text.strip()
            
            numero_capitulo_match = re.search(r"(?:Capítulo|Chapter|Cap)\.?\s*([\d\.]+)", cap_text, re.IGNORECASE)
            if numero_capitulo_match:
                numero_capitulo = float(numero_capitulo_match.group(1))
                lista_de_capitulos.append({
                    "cap_numero": numero_capitulo,
                    "cap_url": cap_url_completa,
                })

        lista_de_capitulos.reverse()
        print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
        return obra_nome, lista_de_capitulos

    except Exception as e:
        print(f"Erro ao buscar informações da obra com Selenium: {e}")
        return None, []


def baixar_capitulo_batoto(chapter_info, driver, base_path):
    """
    Baixa as imagens de um capítulo do Batoto usando Selenium.
    """
    chapter_url = chapter_info["cap_url"]
    chapter_number = chapter_info["cap_numero"]

    # Formatação do nome da pasta
    s_chapter_number = str(chapter_number)
    if "." in s_chapter_number:
        parts = s_chapter_number.split(".")
        integer_part, fractional_part = parts[0], parts[1]
        formatted_number = f"{integer_part.zfill(2)}.{fractional_part}" if fractional_part != '0' else integer_part.zfill(2)
    else:
        formatted_number = s_chapter_number.zfill(2)

    chapter_folder_name = f"Capítulo {formatted_number}"
    chapter_path = os.path.join(base_path, chapter_folder_name)
    os.makedirs(chapter_path, exist_ok=True)

    try:
        print(f"  Acessando página do capítulo {chapter_number}...")
        driver.get(chapter_url)
        wait = WebDriverWait(driver, 20)

        # Espera o contêiner das imagens e pelo menos uma imagem carregar
        wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div#viewer img.page-img"))
        )
        # Uma pequena pausa extra para garantir que os scripts terminem de rodar
        time.sleep(2)

        img_elements = driver.find_elements(By.CSS_SELECTOR, "div#viewer img.page-img")
        if not img_elements:
            print(f"  Nenhuma imagem encontrada para o capítulo {chapter_number}.")
            return 0, 1

        total_images = len(img_elements)
        images_downloaded = 0
        print(f"  Encontradas {total_images} imagens. Iniciando download...")

        for i, img_element in enumerate(img_elements):
            img_url = img_element.get_attribute("src")
            if not img_url:
                continue
            try:
                _, extension = os.path.splitext(img_url.split("?")[0])
                if not extension:
                    extension = ".jpg"
                filename = f"{str(i + 1).zfill(3)}{extension}"
                filepath = os.path.join(chapter_path, filename)

                # Reutilizando a função de download robusta que já existe no seu projeto
                success = download_image_with_session(driver, img_url, filepath)
                if success:
                    images_downloaded += 1
                
                time.sleep(0.2)

            except Exception as e:
                print(f"    -> Erro no download da imagem {i + 1}: {e}")

        print(f"  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas.")
        return images_downloaded, total_images - images_downloaded

    except Exception as e:
        print(f"  Ocorreu um erro ao processar o capítulo {chapter_number} com Selenium: {e}")
        return 0, 1