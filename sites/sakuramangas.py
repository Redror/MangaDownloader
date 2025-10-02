import os
import time
import re
import json
from natsort import natsorted

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

# Importa a nova função de download diretamente do helpers
from helpers import download_image_with_selenium

class number_of_elements_is_greater_than(object):
    def __init__(self, locator, count):
        self.locator = locator
        self.count = count

    def __call__(self, driver):
        try:
            elements = driver.find_elements(*self.locator)
            return len(elements) > self.count
        except StaleElementReferenceException:
            return False

def obter_dados_obra_sakura(obra_url, driver):
    """
    Abre a URL da obra no SakuraMangas, clica no botão "Ver mais" até o fim,
    e então extrai o título e a lista completa de capítulos.
    """
    print(f"Buscando informações da obra em: {obra_url}")
    obra_nome = ""
    try:
        driver.get(obra_url)
        
        seletor_titulo = 'h1.h1-titulo'
        print("    -> Aguardando título da obra ficar visível...")
        titulo_element = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_titulo))
        )
        driver.minimize_window()
        obra_nome = titulo_element.text.strip()
        print(f"    -> Título encontrado: '{obra_nome}'")
        
        seletor_capitulos = 'div.capitulo-lista span.num-capitulo a'
        
        print("    -> Procurando por botão 'Ver mais' para carregar todos os capítulos...")
        while True:
            try:
                botao_ver_mais = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, 'ver-mais'))
                )
                count_antes_do_clique = len(driver.find_elements(By.CSS_SELECTOR, seletor_capitulos))
                driver.execute_script("arguments[0].click();", botao_ver_mais)
                print(f"    -> Botão 'Ver mais' clicado. Esperando novos capítulos... (havia {count_antes_do_clique})")
                try:
                    wait = WebDriverWait(driver, 5) 
                    wait.until(number_of_elements_is_greater_than(
                        (By.CSS_SELECTOR, seletor_capitulos), count_antes_do_clique
                    ))
                except Exception:
                    print("    -> Timeout ao esperar por novos capítulos. Assumindo que todos foram carregados.")
                    break
            except Exception:
                print("    -> Botão 'Ver mais' não encontrado. Todos os capítulos devem ter sido carregados.")
                break
        
        capitulos_elements = driver.find_elements(By.CSS_SELECTOR, seletor_capitulos)
        if not capitulos_elements:
            print("!!! AVISO: Nenhum capítulo encontrado com o seletor atual. O layout do site pode ter mudado.")
            return obra_nome, []

        lista_de_capitulos = []
        for cap_element in capitulos_elements:
            numero_capitulo_str = re.search(r'(\d+(\.\d+)?)', cap_element.text)
            if numero_capitulo_str:
                numero_capitulo = float(numero_capitulo_str.group(1))
                lista_de_capitulos.append({'cap_numero': numero_capitulo, 'cap_url': cap_element.get_attribute('href')})
        
        lista_de_capitulos.reverse()
        print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
        return obra_nome, lista_de_capitulos

    except Exception as e:
        print(f"Erro ao buscar informações da obra com Selenium: {e}")
        return obra_nome, [] 

def baixar_capitulo_sakura(chapter_info, driver, base_path):
    """
    Baixa um capítulo do SakuraMangas combinando a captura de rede com um loop de
    adivinhação para garantir que todas as imagens sejam baixadas.
    """
    chapter_url = chapter_info['cap_url']
    chapter_number = chapter_info['cap_numero']
    
    # Formata o nome da pasta do capítulo
    s_chapter_number = str(chapter_number)
    if '.' in s_chapter_number:
        parts = s_chapter_number.split('.')
        integer_part, fractional_part = parts[0], parts[1]
        formatted_number = f"{integer_part.zfill(2)}.{fractional_part}" if fractional_part != '0' else integer_part.zfill(2)
    else:
        formatted_number = s_chapter_number.zfill(2)
    chapter_folder_name = f"Capítulo {formatted_number}"
    
    chapter_path = os.path.join(base_path, chapter_folder_name)
    os.makedirs(chapter_path, exist_ok=True)
    
    try:
        print(f"  Acessando página do capítulo {chapter_number} e monitorando a rede...")
        driver.get_log('performance')
        driver.get(chapter_url)
        time.sleep(5) 

        logs = driver.get_log('performance')
        
        urls_encontradas = []
        for entry in logs:
            log = json.loads(entry['message'])['message']
            if 'Network.responseReceived' == log['method']:
                url = log['params']['response']['url']
                if 'sakuramangas.org/imagens/' in url:
                    urls_encontradas.append(url)
        
        urls_unicas = natsorted(list(set(urls_encontradas)))

        if not urls_unicas:
            print("  [!] Nenhuma URL de imagem foi capturada nos logs de rede. Tentativa de adivinhação cega falhou.")
            return 0, 1

        # Extrai a "fórmula" da URL a partir da primeira imagem encontrada
        primeira_url = urls_unicas[0]
        match = re.search(r'(https://sakuramangas\.org/imagens/[a-f0-9]+/)((\d+)\.\w+)', primeira_url)
        if not match:
            print("  [!] Não foi possível analisar a estrutura da URL da imagem a partir dos logs.")
            return 0, 1
            
        base_url_com_hash = match.group(1)
        nome_arquivo_exemplo = match.group(2)
        numero_exemplo = match.group(3)
        extensao = os.path.splitext(nome_arquivo_exemplo)[1]
        padding = len(numero_exemplo) # Detecta o número de zeros (ex: 3 para '001')

        print(f"  Estrutura da URL detectada. Iniciando download com adivinhação sequencial...")

        images_downloaded = 0
        consecutive_failures = 0
        page_index = 1

        while consecutive_failures < 3: # Para após 3 falhas seguidas
            # Monta a URL da imagem a ser adivinhada
            page_number_str = str(page_index).zfill(padding)
            img_url = f"{base_url_com_hash}{page_number_str}{extensao}"
            
            filename = f"{page_number_str}{extensao}"
            filepath = os.path.join(chapter_path, filename)
            
            # Tenta baixar a imagem com o método Selenium
            success = download_image_with_selenium(driver, img_url, filepath)
            
            if success:
                images_downloaded += 1
                consecutive_failures = 0 # Reseta o contador de falhas
            else:
                consecutive_failures += 1
                print(f"    -> Falha ao encontrar a imagem {page_index}. Tentativas restantes: {3 - consecutive_failures}")

            page_index += 1
            time.sleep(0.1)

        total_images = images_downloaded
        if total_images > 0:
             print(f"\\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
             return images_downloaded, 0
        else:
            print(f"\\n  [!] Nenhuma imagem pôde ser baixada para o capítulo {chapter_number}.")
            return 0, 1


    except Exception as e:
        print(f"  Ocorreu um erro geral ao processar o capítulo {chapter_number}: {e}")
        return 0, 1