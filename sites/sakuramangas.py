import os
import time
import re
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# -- INÍCIO: Funções de outros módulos adicionadas aqui para autonomia --

def download_image_with_session(driver, image_url, save_path):
    """
    Baixa a imagem usando a sessão de cookies e o User-Agent do driver para parecer um navegador real.
    """
    try:
        session = requests.Session()
        
        # Copia os cookies do driver para a sessão
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        
        # PONTO CHAVE: Obtém o User-Agent do navegador e o adiciona aos headers
        user_agent = driver.execute_script("return navigator.userAgent;")
        session.headers.update({
            'Referer': driver.current_url,
            'User-Agent': user_agent
        })
        
        response = session.get(image_url, stream=True, timeout=15)
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            # Adiciona um print para ajudar a identificar o problema, se persistir
            print(f"      -> Falha no download, status: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        # Silencia o erro de request para não poluir o terminal, a falha já será contada
        return False

# -- FIM: Funções de outros módulos --


class number_of_elements_is_greater_than(object):
    """
    Uma condição de espera do Selenium para verificar se o número de elementos
    encontrados é maior que um número X.
    """
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
    Baixa um capítulo do SakuraMangas usando a lógica de adivinhação de URL.
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
        print(f"  Acessando página do capítulo {chapter_number} para obter link base...")
        driver.get(chapter_url)
        
        # Pega a URL da primeira imagem para extrair o HASH
        seletor_primeira_imagem = '#paginas .pag-item:first-child img'
        primeira_imagem = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_primeira_imagem))
        )
        url_primeira_imagem = primeira_imagem.get_attribute('data-src') or primeira_imagem.get_attribute('src')
        
        # Extrai o hash da URL (ex: '9300128ea653220849639311528eefc2')
        match = re.search(r'/imagens/([a-f0-9]+)/', url_primeira_imagem)
        if not match:
            print("  [!] Não foi possível extrair o hash da URL da imagem. O padrão pode ter mudado.")
            return 0, 1
            
        image_hash = match.group(1)
        print(f"    -> Hash do capítulo encontrado: {image_hash}")
        
        images_downloaded = 0
        consecutive_failures = 0
        page_index = 1

        print(f"  Iniciando download sequencial para o capítulo {chapter_number}...")
        while consecutive_failures < 3: # Para após 3 falhas seguidas
            # Monta a URL (ex: https://sakuramangas.org/imagens/HASH/001.jpg)
            page_number_str = str(page_index).zfill(3)
            img_url = f"https://sakuramangas.org/imagens/{image_hash}/{page_number_str}.jpg"
            
            filename = f"{str(page_index).zfill(3)}.jpg"
            filepath = os.path.join(chapter_path, filename)
            
            # Tenta baixar a imagem
            success = download_image_with_session(driver, img_url, filepath)
            
            if success:
                images_downloaded += 1
                consecutive_failures = 0 # Reseta o contador de falhas
            else:
                consecutive_failures += 1
            
            page_index += 1
            time.sleep(0.2) # Pequena pausa para não sobrecarregar o servidor

        if images_downloaded == 0:
            print(f"  [!] Nenhuma imagem foi encontrada para o capítulo {chapter_number} com este método.")
            return 0, 1

        total_images = images_downloaded
        print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
        return images_downloaded, 0

    except Exception as e:
        print(f"  Ocorreu um erro geral ao processar o capítulo {chapter_number}: {e}")
        return 0, 1