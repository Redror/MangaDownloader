import os
import time
import shutil
import cloudscraper
from natsort import natsorted

# --- Importações dos seus novos módulos ---
from driver_setup import setup_selenium_driver
from conversor import criar_pdf_de_imagens, criar_cbz_de_imagens
from helpers import sanitize_foldername

# --- Importa os módulos de cada site ---
from sites import sussytoons, mangalivre, sakuramangas, manhastro, loverstoon, mediocretoons, batoto

# ==============================================================================
# SEÇÃO PRINCIPAL (ROTEADOR)
# ==============================================================================

def main():
    scraper = cloudscraper.create_scraper()
    driver_selenium = None
    
    while True:
        # O estado do popup do SussyToons não é mais necessário com a abordagem de API
        obra_url = input("Por favor, cole a URL da OBRA e pressione Enter (ou apenas Enter para sair):\n> ")
        if not obra_url:
            break
            
        obra_nome_original = None
        lista_de_capitulos = []
        site_handler = ""
        
        # Define se o navegador deve ser visível (headless=False) ou invisível (headless=True)
        is_problematic_site = "manhastro.net" in obra_url or "loverstoon.com" in obra_url or "mangalivre.tv" in obra_url
        use_headless_mode = not is_problematic_site
        
        # Lógica para identificar o site e obter os dados da obra
        if "sussytoons.wtf" in obra_url or "sussytoons.site" in obra_url:
            # SussyToons agora usa apenas o scraper para obter a lista de capítulos
            site_handler = "sussy_api" # Novo handler para refletir a mudança
            obra_nome_original, lista_de_capitulos = sussytoons.obter_dados_obra_sussy_api(obra_url, scraper)
        elif "mangalivre.tv" in obra_url:
            site_handler = "mangalivre_selenium"
            driver_selenium = setup_selenium_driver(run_headless=use_headless_mode)
            if driver_selenium:
                obra_nome_original, lista_de_capitulos = mangalivre.obter_dados_obra_selenium(obra_url, driver_selenium)
        elif "sakuramangas.org" in obra_url:
            site_handler = "sakura_selenium"
            driver_selenium = setup_selenium_driver(run_headless=use_headless_mode)
            if driver_selenium:
                obra_nome_original, lista_de_capitulos = sakuramangas.obter_dados_obra_sakura(obra_url, driver_selenium)
        elif "manhastro.net" in obra_url:
            site_handler = "manhastro_selenium"
            driver_selenium = setup_selenium_driver(run_headless=use_headless_mode)
            if driver_selenium:
                obra_nome_original, lista_de_capitulos = manhastro.obter_dados_obra_manhastro(obra_url, driver_selenium)
        elif "loverstoon.com" in obra_url:
            site_handler = "loverstoon_selenium"
            driver_selenium = setup_selenium_driver(run_headless=use_headless_mode)
            if driver_selenium:
                obra_nome_original, lista_de_capitulos = loverstoon.obter_dados_obra_loverstoon(obra_url, driver_selenium)
        elif "mediocretoons.com" in obra_url:
            site_handler = "mediocre_api"
            obra_nome_original, lista_de_capitulos = mediocretoons.obter_dados_obra_mediocre(obra_url, scraper)
        elif "bato.to" in obra_url:
            site_handler = "batoto_selenium"
            driver_selenium = setup_selenium_driver(run_headless=use_headless_mode)
            if driver_selenium:
                obra_nome_original, lista_de_capitulos = batoto.obter_dados_obra_batoto(obra_url, driver_selenium)
        else:
            print("URL de um site não suportado. Tente novamente.")
            continue
        
        # Validação dos dados obtidos
        if site_handler not in ["sussy_api"] and driver_selenium is None and (not lista_de_capitulos):
            print("Não foi possível iniciar o navegador ou obter a lista de capítulos. Pulando para a próxima URL.")
            continue
            
        if not lista_de_capitulos: 
            print("Não foi possível obter a lista de capítulos. Pulando para a próxima URL.")
            if driver_selenium:
                driver_selenium.quit()
            continue
            
        obra_folder_name = sanitize_foldername(obra_nome_original)
        if not obra_folder_name:
            print(f"!!! ERRO: Não foi possível obter um nome válido para a obra na URL: {obra_url}")
            if driver_selenium:
                driver_selenium.quit()
            continue
            
        os.makedirs(obra_folder_name, exist_ok=True)
        print(f"Os capítulos serão salvos na pasta principal '{obra_folder_name}'.")
        
        # --- Interface de usuário para escolhas de formato e capítulos ---
        
        print("\nEm qual formato você deseja salvar os capítulos?")
        print("1: Pastas de Imagens (padrão)\n2: Arquivos PDF\n3: Arquivos CBZ\n4: PDF e CBZ")
        format_choice = input("Sua escolha (1-4): ").strip()
        formatos_desejados = []
        if format_choice == '2': formatos_desejados = ['PDF']
        elif format_choice == '3': formatos_desejados = ['CBZ']
        elif format_choice == '4': formatos_desejados = ['PDF', 'CBZ']

        delete_original_folders = False
        if formatos_desejados:
            delete_choice = input("Deseja apagar as pastas de imagens originais após a conversão? (S/N): ").strip().upper()
            if delete_choice == 'S':
                delete_original_folders = True

        print("\nO que você deseja baixar?\n1. Todos os capítulos\n2. Um intervalo de capítulos")
        choice = input("Sua escolha (1 ou 2): ").strip()
        caps_para_baixar = []
        
        if choice == '1':
            caps_para_baixar = lista_de_capitulos
        elif choice == '2':
            try:
                inicio = float(input("Baixar a partir do capítulo nº: "))
                fim = float(input("Até o capítulo nº: "))
                # LÓGICA CORRIGIDA para incluir capítulos fracionados (ex: 5.1, 5.2)
                fim_ajustado = fim + 1
                for cap in lista_de_capitulos:
                    if inicio <= cap['cap_numero'] < fim_ajustado:
                        caps_para_baixar.append(cap)
            except ValueError:
                print("Entrada inválida.")
                if driver_selenium: driver_selenium.quit()
                continue
        else:
            print("Escolha inválida.")
            if driver_selenium: driver_selenium.quit()
            continue
            
        if not caps_para_baixar:
            print("Nenhum capítulo encontrado no intervalo.")
            if driver_selenium: driver_selenium.quit()
            continue

        # A lógica para iniciar um driver para o SussyToons foi REMOVIDA, pois não é mais necessário.
        
        caps_para_baixar.sort(key=lambda x: x['cap_numero'])
        
        # --- Loop de Download ---
        
        total_a_baixar = len(caps_para_baixar)
        total_sucessos = 0
        total_falhas = 0
        print(f"\nIniciando download de {total_a_baixar} capítulos...")
        
        for i, cap_info in enumerate(caps_para_baixar):
            print("-" * 40)
            sucessos, falhas = 0, 0
            
            chapter_number = cap_info['cap_numero']

            if chapter_number.is_integer():
                display_number = int(chapter_number)
            else:
                display_number = chapter_number
            
            print(f"Processando {i + 1}/{total_a_baixar}: Capítulo {display_number}")
            
            # Formatação do nome da pasta (lógica mantida)
            if chapter_number.is_integer():
                formatted_number = str(int(chapter_number)).zfill(2)
            else:
                s_chapter_number = str(chapter_number)
                parts = s_chapter_number.split('.')
                integer_part, fractional_part = parts[0], parts[1]
                formatted_number = f"{integer_part.zfill(2)}.{fractional_part}"
            
            chapter_folder_name = f"Capítulo {formatted_number}"
            chapter_path = os.path.join(obra_folder_name, chapter_folder_name)

            # Lógica de download específica para cada site
            if site_handler == "sussy_api":
                # Agora chama a nova função que usa a API e passa o scraper
                sucessos, falhas = sussytoons.baixar_capitulo_sussy_api(cap_info, scraper, obra_folder_name)
            elif site_handler == "mediocre_api":
                sucessos, falhas = mediocretoons.baixar_capitulo_mediocre(cap_info, scraper, obra_folder_name)
            else: # Para todos os outros sites que usam Selenium
                sucessos, falhas = {
                    "mangalivre_selenium": mangalivre.baixar_capitulo_selenium,
                    "sakura_selenium": sakuramangas.baixar_capitulo_sakura,
                    "manhastro_selenium": manhastro.baixar_capitulo_manhastro,
                    "loverstoon_selenium": loverstoon.baixar_capitulo_loverstoon,
                    "batoto_selenium": batoto.baixar_capitulo_batoto,
                }[site_handler](cap_info, driver_selenium, obra_folder_name)

            total_sucessos += sucessos
            total_falhas += falhas

            # --- LÓGICA DE CONVERSÃO RESTAURADA ---
            if sucessos > 0 and formatos_desejados:
                print(f"  [→] Iniciando conversão para: {', '.join(formatos_desejados)}")
                imagens_na_pasta = natsorted([f for f in os.listdir(chapter_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.avif'))])
                
                conversoes_ok = 0
                if 'PDF' in formatos_desejados:
                    caminho_pdf = os.path.join(obra_folder_name, f"{chapter_folder_name}.pdf")
                    if criar_pdf_de_imagens(imagens_na_pasta, chapter_path, caminho_pdf):
                        conversoes_ok +=1
                
                if 'CBZ' in formatos_desejados:
                    caminho_cbz = os.path.join(obra_folder_name, f"{chapter_folder_name}.cbz")
                    if criar_cbz_de_imagens(imagens_na_pasta, chapter_path, caminho_cbz):
                        conversoes_ok +=1
                
                if delete_original_folders and conversoes_ok == len(formatos_desejados):
                    print(f"  [🗑️] Removendo pasta de imagens original: {chapter_folder_name}")
                    shutil.rmtree(chapter_path)


            time.sleep(1)
            
        print("-" * 40)
        print("\nTodos os downloads solicitados para esta obra foram concluídos!")
        print(f"Total de imagens baixadas com sucesso: {total_sucessos}")
        if total_falhas > 0:
            print(f"Total de imagens que falharam: {total_falhas}")
        print("\n" + "="*50 + "\n")

        # Fecha o navegador ao final de CADA obra, se ele foi utilizado.
        if driver_selenium:
            print("Fechando o navegador (Selenium)...")
            driver_selenium.quit()
            driver_selenium = None

if __name__ == "__main__":

    main()
