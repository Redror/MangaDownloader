import os
import time
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

from helpers import download_image_with_selenium

# Variável para controlar o clique no modo de leitura do SakuraMangas
SAKURA_MODE_SET = False

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
        titulo_element = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_titulo))
        )
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
    Baixa um capítulo do SakuraMangas, lidando com "Infinite Scroll", "Lazy Loading",
    e transferindo cookies para evitar o erro 403 Forbidden.
    """
    global SAKURA_MODE_SET
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
        time.sleep(5)

        if not SAKURA_MODE_SET:
            try:
                print("    -> Verificando o modo de leitura...")
                scroll_mode_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span.div-modo.div-scroll'))
                )
                
                # --- LÓGICA DE VERIFICAÇÃO DE ESTILO ADICIONADA ---
                style_attribute = scroll_mode_button.get_attribute('style')
                if "rgb(255, 160, 226)" in style_attribute:
                    print("    -> Modo Scroll já está ativo.")
                    SAKURA_MODE_SET = True
                else:
                    scroll_mode_button.click()
                    print("    -> Modo de leitura alterado para Scroll.")
                    SAKURA_MODE_SET = True
                    time.sleep(2)
            except Exception:
                print("    -> Não foi possível encontrar o botão de modo Scroll (pode não existir).")

        print("    -> Rolando para carregar todas as imagens...")
        scroll_pause_time = 1
        screen_height = driver.execute_script("return window.screen.height;")
        i = 1
        
        while True:
            driver.execute_script(f"window.scrollTo(0, {screen_height * i});")
            i += 1
            time.sleep(scroll_pause_time)
            scroll_height = driver.execute_script("return document.body.scrollHeight;")
            if (screen_height * (i-1)) > scroll_height:
                print("    -> Fim da página alcançado.")
                break
        
        seletor_imagens = '#paginas .pag-item img'
        paginas_elements = driver.find_elements(By.CSS_SELECTOR, seletor_imagens)
        
        if not paginas_elements:
            print(f"  Nenhuma imagem encontrada para o capítulo {chapter_number}.")
            return 0, 0
            
        print(f"  Encontradas {len(paginas_elements)} imagens. Iniciando download via Navegador...")
        
        images_downloaded = 0
        total_images = len(paginas_elements)
        
        for i, pagina_element in enumerate(paginas_elements):
            try:
                img_url = pagina_element.get_attribute('data-src') or pagina_element.get_attribute('src')
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