import os
import time
import re
import requests
import base64
import cloudscraper

# --- Importações para o Selenium ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# --- Importação para evitar a detecção do Selenium ---
import undetected_chromedriver as uc


# ==============================================================================
# SEÇÃO 1: VARIÁVEIS GLOBAIS E CLASSES AUXILIARES
# ==============================================================================

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

def sanitize_foldername(name):
    """Remove caracteres inválidos de um nome de arquivo/pasta."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

# ==============================================================================
# FUNÇÃO FINAL PARA CONTORNAR A DETECÇÃO
# ==============================================================================
def setup_selenium_driver():
    """
    Configura e retorna uma instância do driver com injeção de script
    para neutralizar e travar a proteção anti-bot.
    """
    print("Iniciando o navegador")
    
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--log-level=3')

    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                const originalSetInterval = window.setInterval;
                window.setInterval = (handler, timeout, ...args) => {
                    const handlerStr = handler.toString();
                    if (handlerStr.includes('isSuspend') && handlerStr.includes('detect')) {
                        // Bloqueia o timer do disable-devtool
                        console.log('Timer do DisableDevtool bloqueado.');
                        return null;
                    }
                    // Permite que outros timers funcionem
                    return originalSetInterval(handler, timeout, ...args);
                };
            """
        })

    except Exception as e:
        print(f"!!! ERRO ao iniciar o undetected-chromedriver: {e}")
        print("!!! Verifique se o Google Chrome está instalado e tente novamente.")
        return None
        
    return driver
# ==============================================================================


def download_image_with_selenium(driver, image_url, save_path):
    """
    Usa o Selenium para baixar uma imagem executando um script JavaScript.
    """
    try:
        js_script = """
        var url = arguments[0];
        var callback = arguments[1];
        
        fetch(url)
            .then(response => response.blob())
            .then(blob => {
                var reader = new FileReader();
                reader.onload = function() {
                    callback(this.result);
                };
                reader.readAsDataURL(blob);
            })
            .catch(error => callback(null));
        """
        driver.set_script_timeout(30)
        base64_data = driver.execute_async_script(js_script, image_url)
        
        if base64_data is None:
            print(f"    -> Falha ao obter dados da imagem (retorno nulo do JS) para: {image_url}")
            return False

        header, encoded = base64_data.split(",", 1)
        image_data = base64.b64decode(encoded)
        
        with open(save_path, 'wb') as f:
            f.write(image_data)
        return True
        
    except Exception as e:
        print(f"    -> Erro na função download_image_with_selenium para '{image_url}': {e}")
        return False
        
# ==============================================================================
# SEÇÃO 2: MÓDULO DO SITE SussyToons (API)
# ==============================================================================

def obter_dados_obra_api(obra_id, scraper_session):
    """Obtém os dados de uma obra do SussyToons via API."""
    api_url = f"https://api.sussytoons.wtf/obras/{obra_id}"
    print(f"Buscando informações da obra em: {api_url}")
    try:
        response = scraper_session.get(api_url)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            resultado = data['resultado']
            obra_nome = resultado.get('obr_nome', f"obra_{obra_id}")
            capitulos = resultado.get('capitulos', [])
            capitulos.reverse()
            print(f"Obra encontrada: '{obra_nome}' com {len(capitulos)} capítulos.")
            return obra_nome, capitulos
        return None, None
    except Exception as e:
        print(f"Erro ao buscar informações da obra: {e}")
        return None, None

def baixar_capitulo_api(chapter_id, scraper_session, base_path):
    """Baixa um único capítulo do SussyToons via API."""
    api_url = f"https://api.sussytoons.wtf/capitulos/{chapter_id}"
    try:
        response = scraper_session.get(api_url)
        response.raise_for_status()
        data = response.json()
        if not data.get('success') or 'resultado' not in data:
            print(f"  Falha ao obter dados para o capítulo ID {chapter_id}.")
            return 0, 1
        resultado = data['resultado']
        paginas = resultado.get('cap_paginas', [])
        chapter_number = resultado.get('cap_numero')
        if not paginas:
            print(f"  Nenhuma imagem encontrada para o capítulo {chapter_number}.")
            return 0, 0
        obra_id = resultado['obra']['obr_id']
        scan_id = resultado['obra']['scan_id']
        chapter_folder_name = f"Capítulo {str(chapter_number).zfill(2)}"
        chapter_path = os.path.join(base_path, chapter_folder_name)
        os.makedirs(chapter_path, exist_ok=True)
        print(f"  Baixando {len(paginas)} imagens para a pasta '{chapter_folder_name}'...")
        images_downloaded = 0
        for i, pagina in enumerate(paginas):
            try:
                filename_from_api = pagina['src']
                if not filename_from_api: continue
                if '/' in filename_from_api:
                    base_image_url = "https://cdn.sussytoons.site/wp-content/uploads/WP-manga/data"
                    full_image_url = base_image_url + filename_from_api
                else:
                    base_image_url = f"https://cdn.sussytoons.site/scans/{scan_id}/obras/{obra_id}/capitulos/{chapter_number}/"
                    full_image_url = base_image_url + filename_from_api
                base_name = filename_from_api.split('?')[0].split('/')[-1]
                _, extension = os.path.splitext(base_name)
                if not extension: extension = '.jpg'
                new_sequential_filename = f"{str(i + 1).zfill(2)}{extension}"
                filepath = os.path.join(chapter_path, new_sequential_filename)
                img_response = scraper_session.get(full_image_url, stream=True)
                img_response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in img_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                images_downloaded += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"\n    -> Erro ao baixar a imagem {i+1} de '{full_image_url}': {e}")
        print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{len(paginas)} imagens baixadas com sucesso.")
        return images_downloaded, len(paginas) - images_downloaded
    except Exception as e:
        print(f"  Ocorreu um erro geral ao processar o capítulo {chapter_id}: {e}")
        return 0, 1

# ==============================================================================
# SEÇÃO 3: MÓDULO DO SITE MangaLivre.tv
# ==============================================================================

def obter_dados_obra_selenium(obra_url, driver):
    """Abre a URL da obra no MangaLivre, clica em 'Mostrar mais' e extrai os dados."""
    print(f"Buscando informações da obra em: {obra_url}")
    try:
        driver.get(obra_url)
        seletor_titulo = 'div.post-title h1'
        titulo_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, seletor_titulo)))
        obra_nome = titulo_element.text.strip()
        print("    -> Procurando por botão 'Mostrar mais' para carregar todos os capítulos...")
        while True:
            try:
                botao_mostrar_mais = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.chapter-readmore'))
                )
                botao_mostrar_mais.click()
                print("    -> Botão 'Mostrar mais' clicado.")
                time.sleep(1.5)
            except Exception:
                print("    -> Todos os capítulos foram carregados.")
                break
        seletor_capitulos = 'li.wp-manga-chapter a'
        capitulos_elements = driver.find_elements(By.CSS_SELECTOR, seletor_capitulos)
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

# ==============================================================================
# SEÇÃO 4: MÓDULO DO SITE SakuraMangas.org
# ==============================================================================

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
        # Aumentado o tempo de espera para 15s para dar margem a conexões mais lentas
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

def baixar_capitulo_scroll(chapter_info, driver, base_path):
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
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.div-modo div-scroll'))
                )
                scroll_mode_button.click()
                print("    -> Modo de leitura alterado para Scroll.")
                SAKURA_MODE_SET = True
                time.sleep(2)
            except Exception:
                print("    -> Não foi possível clicar no botão de modo Scroll (pode já estar ativo ou não existir).")

        print("    -> Rolando para carregar todas as imagens...")
        scroll_pause_time = 2
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

# ==============================================================================
# SEÇÃO 5: FUNÇÃO PRINCIPAL (ROTEADOR)
# ==============================================================================

def main():
    scraper = cloudscraper.create_scraper()
    driver_selenium = None
    while True:
        obra_url = input("Por favor, cole a URL da OBRA e pressione Enter (ou apenas Enter para sair):\n> ")
        if not obra_url:
            break
        obra_nome_original = None
        lista_de_capitulos = []
        site_handler = ""
        if "sussytoons.wtf" in obra_url:
            site_handler = "api"
            try:
                obra_id = obra_url.strip('/').split('/obra/')[1].split('/')[0]
                if not obra_id.isdigit(): raise ValueError
                obra_nome_original, lista_de_capitulos = obter_dados_obra_api(obra_id, scraper)
            except (IndexError, ValueError):
                print("URL da obra (SussyToons) inválida. Tente novamente."); continue
        elif "mangalivre.tv" in obra_url:
            site_handler = "selenium"
            if driver_selenium is None:
                driver_selenium = setup_selenium_driver()
            obra_nome_original, lista_de_capitulos = obter_dados_obra_selenium(obra_url, driver_selenium)
        elif "sakuramangas.org" in obra_url:
            site_handler = "selenium_scroll"
            if driver_selenium is None:
                driver_selenium = setup_selenium_driver()
            obra_nome_original, lista_de_capitulos = obter_dados_obra_sakura(obra_url, driver_selenium)
        else:
            print("URL de um site não suportado. Tente novamente."); continue
        
        if site_handler in ["selenium", "selenium_scroll"] and driver_selenium is None:
            print("Não foi possível iniciar o navegador. Pulando para a próxima URL.")
            continue
            
        if not lista_de_capitulos: 
            print("Não foi possível obter a lista de capítulos. Pulando para a próxima URL.")
            continue
        obra_folder_name = sanitize_foldername(obra_nome_original)
        if not obra_folder_name:
            print(f"!!! ERRO: Não foi possível obter um nome válido para a obra na URL: {obra_url}")
            print("!!!      O seletor de título pode estar incorreto. Pulando esta obra.")
            continue
        os.makedirs(obra_folder_name, exist_ok=True)
        print(f"Os capítulos serão salvos na pasta principal '{obra_folder_name}'.")
        print("\nO que você deseja baixar?\n1. Todos os capítulos\n2. Um intervalo de capítulos")
        choice = input("Sua escolha (1 ou 2): ")
        caps_para_baixar = []
        if choice == '1': caps_para_baixar = lista_de_capitulos
        elif choice == '2':
            try:
                inicio = float(input("Baixar a partir do capítulo nº: "))
                fim = float(input("Até o capítulo nº: "))
                for cap in lista_de_capitulos:
                    if inicio <= cap['cap_numero'] <= fim: caps_para_baixar.append(cap)
            except ValueError:
                print("Entrada inválida."); continue
        else:
            print("Escolha inválida."); continue
        if not caps_para_baixar:
            print("Nenhum capítulo encontrado no intervalo."); continue
        total_a_baixar = len(caps_para_baixar)
        total_sucessos = 0
        total_falhas = 0
        print(f"\nIniciando download de {total_a_baixar} capítulos...")
        for i, cap_info in enumerate(caps_para_baixar):
            print("-" * 40)
            sucessos, falhas = 0, 0
            if site_handler == "api":
                print(f"Processando {i + 1}/{total_a_baixar}: Capítulo {cap_info['cap_numero']} (ID: {cap_info['cap_id']})")
                sucessos, falhas = baixar_capitulo_api(cap_info['cap_id'], scraper, obra_folder_name)
            elif site_handler == "selenium":
                print(f"Processando {i + 1}/{total_a_baixar}: Capítulo {cap_info['cap_numero']}")
                sucessos, falhas = baixar_capitulo_selenium(cap_info, driver_selenium, obra_folder_name)
            elif site_handler == "selenium_scroll":
                print(f"Processando {i + 1}/{total_a_baixar}: Capítulo {cap_info['cap_numero']}")
                sucessos, falhas = baixar_capitulo_scroll(cap_info, driver_selenium, obra_folder_name)
            total_sucessos += sucessos
            total_falhas += falhas
            time.sleep(1)
        print("-" * 40)
        print("\nTodos os downloads solicitados para esta obra foram concluídos!")
        print(f"Total de imagens baixadas com sucesso: {total_sucessos}")
        if total_falhas > 0:
            print(f"Total de imagens que falharam: {total_falhas}")
        print("\n" + "="*50 + "\n")
    if driver_selenium:
        print("Fechando o navegador (Selenium)...")
        driver_selenium.quit()

if __name__ == "__main__":
    main()
