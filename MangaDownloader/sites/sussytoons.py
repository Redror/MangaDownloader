import os
import re
import time
import requests # Adicionado para o método de adivinhação

def obter_dados_obra_sussy_api(obra_url, scraper_session):
    """Obtém a lista de capítulos do SussyToons via API, incluindo o cap_id necessário."""
    print(f"Buscando lista de capítulos via API para: {obra_url}")
    try:
        obra_id_match = re.search(r'/obra/(\d+)', obra_url)
        if not obra_id_match:
            print("!!! ERRO: Não foi possível extrair o ID da obra da URL.")
            return None, []
        
        obra_id = obra_id_match.group(1)
        api_url = f"https://api.sussytoons.wtf/obras/{obra_id}"
        
        response = scraper_session.get(api_url, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get('success'):
            resultado = data.get('resultado', {})
            obra_nome = resultado.get('obr_nome', f"obra_{obra_id}")
            capitulos_api = resultado.get('capitulos', [])
            
            lista_de_capitulos = []
            for cap in capitulos_api:
                cap_id = cap.get('cap_id')
                if not cap_id:
                    continue

                lista_de_capitulos.append({
                    'cap_numero': float(cap['cap_numero']),
                    'cap_url': f"https://www.sussytoons.wtf/capitulo/{cap_id}",
                    'cap_id': cap_id,
                    'obra_id': obra_id # Adicionando o obra_id para o método de adivinhação
                })

            lista_de_capitulos.reverse()
            print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
            return obra_nome, lista_de_capitulos
        else:
            print(f"!!! A API retornou um erro: {data.get('message', 'Erro desconhecido')}")
            return None, []
    except Exception as e:
        print(f"Erro ao buscar informações da obra via API: {e}")
        return None, []

def baixar_capitulo_sussy_api(chapter_info, scraper_session, base_path):
    """
    Baixa um capítulo do SussyToons. Tenta via API primeiro, e se falhar,
    usa o método de adivinhação de URL como fallback.
    """
    chapter_number = chapter_info['cap_numero']
    cap_id = chapter_info['cap_id']
    obra_id = chapter_info['obra_id']
    
    # Formatação do nome da pasta
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
    
    # --- TENTATIVA 1: MÉTODO API (PREFERENCIAL) ---
    try:
        print(f"  Buscando dados do capítulo {chapter_number} via API...")
        chapter_api_url = f"https://api.sussytoons.wtf/capitulos/{cap_id}"
        response = scraper_session.get(chapter_api_url, timeout=20)
        response.raise_for_status()
        data = response.json()

        paginas = []
        if data.get('success'):
            paginas = data.get('resultado', {}).get('cap_paginas', [])

        if paginas:
            print(f"  Encontradas {len(paginas)} imagens via API. Iniciando download...")
            images_downloaded = 0
            total_images = len(paginas)
            
            for i, pagina in enumerate(paginas):
                try:
                    img_src = pagina.get('src')
                    img_path = pagina.get('path')
                    if not img_src or not img_path:
                        print(f"\n    -> Dados da imagem {i+1} estão incompletos. Pulando.")
                        continue

                    # LÓGICA DE MONTAGEM DE URL CORRIGIDA
                    if img_src.startswith('/'):
                        # FORMATO ANTIGO CORRIGIDO
                        img_url = f"https://cdn.sussytoons.site/wp-content/uploads/WP-manga/data{img_src}"
                    else:
                        # FORMATO NOVO
                        img_url = f"https://cdn.sussytoons.site{img_path}/{img_src}"
                    
                    img_url = img_url.replace('//', '/').replace(':/', '://')

                    _, extension = os.path.splitext(img_src.split('?')[0])
                    if not extension: extension = '.jpg'
                    filename = f"{str(i + 1).zfill(3)}{extension}"
                    filepath = os.path.join(chapter_path, filename)
                    
                    img_response = scraper_session.get(img_url, stream=True, timeout=30)
                    img_response.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    images_downloaded += 1
                    time.sleep(0.1)

                except Exception as e:
                    print(f"\n    -> Erro no loop de download para a imagem {i+1}: {e}")
            
            print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
            return images_downloaded, total_images - images_downloaded
        
        else:
            # Se a API retornou sucesso mas a lista de páginas está vazia
            print(f"  Nenhuma página encontrada para o capítulo {chapter_number} na resposta da API.")
            raise ValueError("Fallback para método de adivinhação")

    except Exception:
        # --- TENTATIVA 2: MÉTODO DE ADIVINHAÇÃO (FALLBACK) ---
        print("  -> API falhou ou não retornou páginas. Tentando método de adivinhação para capítulo bloqueado...")
        
        images_downloaded = 0
        
        if s_chapter_number.endswith('.0'):
            chapter_url_part = s_chapter_number[:-2]
        else:
            chapter_url_part = s_chapter_number.replace('.', '_')
        
        base_url = f"https://cdn.sussytoons.site/scans/1/obras/{obra_id}/capitulos/{chapter_url_part}/"
        formats_to_try = ["{:02d}.jpg", "{:02d}.jpeg", "{:02d}.webp", "{:02d}.png"]
        
        page_index = 0
        consecutive_failures = 0
        while consecutive_failures < 3: # Para de tentar após 3 falhas seguidas
            image_found_for_index = False
            for fmt in formats_to_try:
                page_filename = fmt.format(page_index)
                img_url = base_url + page_filename
                try:
                    img_response = scraper_session.get(img_url, stream=True, timeout=5)
                    if img_response.status_code == 200:
                        extension = os.path.splitext(page_filename)[1]
                        filepath = os.path.join(chapter_path, f"{str(page_index + 1).zfill(3)}{extension}")
                        with open(filepath, 'wb') as f:
                            for chunk in img_response.iter_content(1024):
                                f.write(chunk)
                        images_downloaded += 1
                        image_found_for_index = True
                        consecutive_failures = 0 # Reseta o contador de falhas
                        break 
                except requests.exceptions.RequestException:
                    continue

            if not image_found_for_index:
                consecutive_failures += 1
            
            page_index += 1

        if images_downloaded == 0:
            print(f"  [!] Nenhuma imagem foi encontrada para o capítulo {chapter_number} com o método de adivinhação.")
            print(f"      -> URL base testada: {base_url}")
            return 0, 1

        total_images = images_downloaded
        print(f"\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas (via adivinhação).")
        return images_downloaded, 0