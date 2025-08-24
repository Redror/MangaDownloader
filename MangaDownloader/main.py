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
from sites import sussytoons, mangalivre, sakuramangas, comick

# ==============================================================================
# SEÇÃO PRINCIPAL (ROTEADOR)
# ==============================================================================

def main():
    global SUSSY_TERMS_ACCEPTED
    scraper = cloudscraper.create_scraper()
    driver_selenium = None
    
    while True:
        # Reseta o estado do popup a cada nova obra
        sussytoons.SUSSY_TERMS_ACCEPTED = False
        obra_url = input("Por favor, cole a URL da OBRA e pressione Enter (ou apenas Enter para sair):\n> ")
        if not obra_url:
            break
            
        obra_nome_original = None
        lista_de_capitulos = []
        site_handler = ""
        
        is_problematic_site = "comick.io" in obra_url
        use_headless_mode = not is_problematic_site
        
        if "sussytoons.wtf" in obra_url or "sussytoons.site" in obra_url:
            site_handler = "sussy_hybrid"
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
        elif "comick.io" in obra_url:
            site_handler = "comick_selenium"
            driver_selenium = setup_selenium_driver(run_headless=use_headless_mode)
            if driver_selenium:
                obra_nome_original, lista_de_capitulos = comick.obter_dados_obra_comick(obra_url, driver_selenium)
        else:
            print("URL de um site não suportado. Tente novamente.")
            continue
        
        if site_handler not in ["sussy_hybrid"] and driver_selenium is None and (not lista_de_capitulos):
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
                for cap in lista_de_capitulos:
                    if inicio <= cap['cap_numero'] <= fim:
                        caps_para_baixar.append(cap)
            except ValueError:
                print("Entrada inválida.")
                if driver_selenium:
                    driver_selenium.quit()
                continue
        else:
            print("Escolha inválida.")
            if driver_selenium:
                driver_selenium.quit()
            continue
            
        if not caps_para_baixar:
            print("Nenhum capítulo encontrado no intervalo.")
            if driver_selenium:
                driver_selenium.quit()
            continue
        
        # Inicia o driver do Selenium apenas se for necessário para o download de algum capítulo DISPONÍVEL
        needs_selenium_for_download = any(
            (site_handler == "sussy_hybrid" and cap.get('cap_disponivel', True)) for cap in caps_para_baixar
        )
        if needs_selenium_for_download and driver_selenium is None:
             driver_selenium = setup_selenium_driver(run_headless=True) # Sussy pode rodar em headless
             if driver_selenium is None:
                 print("Falha ao iniciar o Selenium para o download. Pulando obra.")
                 continue

        caps_para_baixar.sort(key=lambda x: x['cap_numero'])
        
        total_a_baixar = len(caps_para_baixar)
        total_sucessos = 0
        total_falhas = 0
        print(f"\nIniciando download de {total_a_baixar} capítulos...")
        
        for i, cap_info in enumerate(caps_para_baixar):
            print("-" * 40)
            sucessos, falhas = 0, 0
            
            print(f"Processando {i + 1}/{total_a_baixar}: Capítulo {cap_info['cap_numero']}")

            chapter_number = cap_info['cap_numero']
            s_chapter_number = str(chapter_number)
            if '.' in s_chapter_number:
                parts = s_chapter_number.split('.')
                integer_part, fractional_part = parts[0], parts[1]
                if fractional_part == '0': formatted_number = integer_part.zfill(2)
                else: formatted_number = f"{integer_part.zfill(2)}.{fractional_part}"
            else: formatted_number = s_chapter_number.zfill(2)
            chapter_folder_name = f"Capítulo {formatted_number}"
            chapter_path = os.path.join(obra_folder_name, chapter_folder_name)

            if site_handler == "sussy_hybrid":
                if cap_info.get('cap_disponivel', True):
                    sucessos, falhas = sussytoons.baixar_capitulo_sussy_selenium(cap_info, driver_selenium, obra_folder_name)
                else:
                    sucessos, falhas = sussytoons.baixar_capitulo_sussy_bloqueado(cap_info, scraper, obra_folder_name)
            elif site_handler == "mangalivre_selenium":
                sucessos, falhas = mangalivre.baixar_capitulo_selenium(cap_info, driver_selenium, obra_folder_name)
            elif site_handler == "sakura_selenium":
                sucessos, falhas = sakuramangas.baixar_capitulo_sakura(cap_info, driver_selenium, obra_folder_name)
            elif site_handler == "comick_selenium":
                sucessos, falhas = comick.baixar_capitulo_comick(cap_info, driver_selenium, obra_folder_name)

            total_sucessos += sucessos
            total_falhas += falhas

            # Conversão após o download
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

        # Fecha o navegador ao final de cada download de obra
        if driver_selenium:
            print("Fechando o navegador (Selenium)...")
            driver_selenium.quit()
            driver_selenium = None

if __name__ == "__main__":
    main()