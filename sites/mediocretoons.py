import os
import re
import time

# Headers necessários para a comunicação com a API da Mediocretoons
MEDIOCRE_HEADERS = {
    'Accept': '*/*',
    'Authorization': 'Bearer null',
    'Origin': 'https://mediocretoons.com',
    'Referer': 'https://mediocretoons.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    'X-App-Key': 'toons-mediocre-app',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
}

def obter_dados_obra_mediocre(obra_url, scraper_session):
    """Obtém a lista de capítulos da Mediocretoons via API."""
    print(f"Buscando lista de capítulos via API para: {obra_url}")
    try:
        obra_id_match = re.search(r'/work/(\d+)', obra_url)
        if not obra_id_match:
            print("!!! ERRO: Não foi possível extrair o ID da obra da URL.")
            return None, []
        
        obra_id = obra_id_match.group(1)
        api_url = f"https://api.mediocretoons.com/obras/{obra_id}"
        
        # Adiciona os headers específicos para a Mediocretoons na sessão
        scraper_session.headers.update(MEDIOCRE_HEADERS)
        
        response = scraper_session.get(api_url, timeout=20)
        response.raise_for_status()
        data = response.json()

        obra_nome = data.get('nome', f"obra_{obra_id}")
        capitulos_api = data.get('capitulos', [])
        
        lista_de_capitulos = []
        for cap in capitulos_api:
            cap_id = cap.get('id')
            if not cap_id:
                continue

            lista_de_capitulos.append({
                'cap_numero': float(cap['numero']),
                'cap_url': f"https://mediocretoons.com/chapter/{cap_id}",
                'cap_id': cap_id,
                'obra_id': obra_id
            })

        lista_de_capitulos.reverse()
        print(f"Obra encontrada: '{obra_nome}' com {len(lista_de_capitulos)} capítulos.")
        return obra_nome, lista_de_capitulos
        
    except Exception as e:
        print(f"Erro ao buscar informações da obra via API: {e}")
        return None, []

def baixar_capitulo_mediocre(chapter_info, scraper_session, base_path):
    """Baixa um capítulo da Mediocretoons via API."""
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
    
    try:
        print(f"  Buscando dados do capítulo {chapter_number} via API...")
        chapter_api_url = f"https://api.mediocretoons.com/capitulos/{cap_id}"
        
        # Garante que os headers estão na sessão
        scraper_session.headers.update(MEDIOCRE_HEADERS)

        response = scraper_session.get(chapter_api_url, timeout=20)
        response.raise_for_status()
        data = response.json()

        paginas = data.get('paginas', [])

        if paginas:
            print(f"  Encontradas {len(paginas)} imagens via API. Iniciando download...")
            images_downloaded = 0
            total_images = len(paginas)
            
            for i, pagina in enumerate(paginas):
                try:
                    img_src = pagina.get('src')
                    if not img_src:
                        print(f"\\n    -> SRC da imagem {i+1} está vazio. Pulando.")
                        continue

                    # Monta a URL da imagem
                    numero_cap = s_chapter_number.replace('.0', '')
                    img_url = f"https://cdn.mediocretoons.com/obras/{obra_id}/capitulos/{numero_cap}/{img_src}"
                    
                    _, extension = os.path.splitext(img_src.split('?')[0])
                    if not extension: extension = '.webp' # Padrão do site
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
                    print(f"\\n    -> Erro no loop de download para a imagem {i+1}: {e}")
            
            print(f"\\n  Capítulo {chapter_number}: {images_downloaded}/{total_images} imagens baixadas com sucesso.")
            return images_downloaded, total_images - images_downloaded
        
        else:
            print(f"  Nenhuma página encontrada para o capítulo {chapter_number} na resposta da API.")
            return 0, 1

    except Exception as e:
        print(f"  Ocorreu um erro geral ao processar o capítulo {chapter_number}: {e}")
        return 0, 1
