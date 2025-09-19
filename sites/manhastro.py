import os
import time
import re
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from helpers import download_image_with_selenium # Mantido para fallback se necessário

def do_login_manhastro(driver):
    """Executa o processo de login no Manhastro de forma mais 'humana'."""
    try:
        print("    -> Redirecionado para a página de login. Realizando autenticação...")
        driver.maximize_window()
        time.sleep(1) # Pausa inicial para a página carregar completamente
        driver.minimize_window()
        user_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Email ou usuário"]'))
        )
        print("    -> Preenchendo usuário...")
        user_input.send_keys("Teste123")
        time.sleep(1)

        pass_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Senha"]')
        print("    -> Preenchendo senha...")
        pass_input.send_keys("Teste123")
        time.sleep(1)

        print("    -> Marcando 'Lembrar-me'...")
        driver.find_element(By.ID, 'rememberMe').click()
        # A pausa aqui é importante para os scripts da página, incluindo o Cloudflare, reagirem.
        time.sleep(3) 

        # A espera explícita pelo #success foi removida conforme solicitado.
        
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        print("    -> Aguardando redirecionamento para a página inicial...")
        WebDriverWait(driver, 20).until(
            EC.url_to_be('https://manhastro.net/')
        )
        print("      -> Login efetuado e redirecionado para a página inicial.")
        return True
        
    except Exception as e:
        print(f"!!! ERRO CRÍTICO durante o processo de login: {e}")
        return False

def obter_dados_obra_manhastro(obra_url, driver):
    """Obtém os dados da obra do site Manhastro de forma mais robusta."""
    print(f"Buscando informações da obra em: {obra_url}")

    try:
        driver.get(obra_url)
        time.sleep(1)
        if "/login" in driver.current_url:
            if do_login_manhastro(driver):
                print("     -> Navegando para a URL da obra após o login...")
                driver.get(obra_url)
            else:
                return "Erro de Login", []

        wait = WebDriverWait(driver, 20)

        driver.maximize_window()
        print("     -> Aguardando título da obra...")
        seletor_titulo = 'h1.text-3xl.font-bold.text-white'
        titulo_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_titulo))
        )
        obra_nome = titulo_element.text.strip()
        print(f"     -> Título encontrado: '{obra_nome}'")

        print("     -> Aguardando lista de capítulos...")

        seletor_capitulos = 'a[href*="/chapter/"]'

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_capitulos)))

        time.sleep(1)

        capitulos_elements = driver.find_elements(By.CSS_SELECTOR, seletor_capitulos)

        if not capitulos_elements:
            print("!!! AVISO: Nenhum capítulo encontrado com o novo seletor.")
            return obra_nome, []

        lista_de_capitulos = []
        for cap_element in capitulos_elements:
            try:
                texto_capitulo = cap_element.find_element(By.CSS_SELECTOR, "span.text-white").text
                numero_capitulo_str = re.search(r'(\d+(\.\d+)?)', texto_capitulo)

                if numero_capitulo_str:
                    numero_capitulo = float(numero_capitulo_str.group(1))
                    lista_de_capitulos.append({
                        'cap_numero': numero_capitulo,
                        'cap_url': cap_element.get_attribute('href')
                    })
            except Exception:
                continue
        
        lista_de_capitulos.reverse()
        print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
        driver.minimize_window()        
        return obra_nome, lista_de_capitulos


    except Exception as e:
        print(f"Erro ao buscar informações da obra com Selenium: {e}")
        return None, []


def download_image_with_session(driver, image_url, save_path):
    """Baixa a imagem usando a sessão de cookies do driver para evitar corrupção."""
    try:
        # Cria uma sessão de requests
        session = requests.Session()
        # Transfere os cookies do Selenium para a sessão
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        # Adiciona o referer, que às vezes é necessário
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

def baixar_capitulo_manhastro(chapter_info, driver, base_path):
    """Baixa um capítulo do Manhastro."""
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
        
        seletor_container_imagens = 'div.w-full.flex.flex-col'
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_container_imagens))
        )
        time.sleep(4)

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
                
                # Usa a nova função de download robusta
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