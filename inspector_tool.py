import time
from driver_setup import setup_selenium_driver

def run_visible_browser_for_inspection(url):
    """
    Inicializa um navegador Selenium visível, navega para uma URL
    e a mantém aberta para inspeção manual.
    """
    driver = None
    try:
        # Inicializa o driver em modo visível (não-headless)
        print("Iniciando o navegador em modo visível...")
        driver = setup_selenium_driver(run_headless=False)
        if not driver:
            print("Falha ao inicializar o driver do navegador.")
            return

        print(f"Navegando para: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("A janela do navegador está aberta e pronta para uso.")
        print("Você pode interagir com a página para fazer o redirecionamento.")
        print("As ferramentas de desenvolvedor (DevTools) devem estar funcionando.")
        print("\nQuando terminar sua análise, pressione Enter nesta janela do terminal")
        print("para fechar o navegador de forma segura.")
        print("="*60)
        
        # Mantém o script rodando até que o usuário pressione Enter
        input()

    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        if driver:
            print("Fechando o navegador.")
            driver.quit()

if __name__ == "__main__":
    # URL de redirecionamento fornecida
    redirect_url = "https://adspublicidades.agency/guardian.php?auth=eyJ1cmwiOiJodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL3dwLWNvbnRlbnRcL3VwbG9hZHNcL1dQLW1hbmdhXC9kYXRhXC9tYW5nYV82OGI4ZmFhMWM3Njg2XC9lMzQ0ZDY3MmE3YzA2OWZiZmU5NDk4Y2I1ZGQxNDQ4OVwvMDAtY29weS5qcGc7aHR0cHM6XC9cL2xvdmVyc3Rvb24uY29tXC93cC1jb250ZW50XC91cGxvYWRzXC9XUC1tYW5nYVwvZGF0YVwvbWFuZ2FfNjhiOGZhYTFjNzY4NlwvZTM0NGQ2NzJhN2MwNjlmYmZlOTQ5OGNiNWRkMTQ0ODlcLzAxLWNvcHkuanBnO2h0dHBzOlwvXC9sb3ZlcnN0b29uLmNvbVwvd3AtY29udGVudFwvdXBsb2Fkc1wvV1AtbWFuZ2FcL2RhdGFcL21hbmdhXzY4YjhmYWExYzc2ODZcL2UzNDRkNjcyYTdjMDY5ZmJmZTk0OThjYjVkZDE0NDg5XC8wMi1jb3B5LmpwZztodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL3dwLWNvbnRlbnRcL3VwbG9hZHNcL1dQLW1hbmdhXC9kYXRhXC9tYW5nYV82OGI4ZmFhMWM3Njg2XC9lMzQ0ZDY3MmE3YzA2OWZiZmU5NDk4Y2I1ZGQxNDQ4OVwvMDMtY29weS5qcGc7aHR0cHM6XC9cL2xvdmVyc3Rvb24uY29tXC93cC1jb250ZW50XC91cGxvYWRzXC9XUC1tYW5nYVwvZGF0YVwvbWFuZ2FfNjhiOGZhYTFjNzY4NlwvZTM0NGQ2NzJhN2MwNjlmYmZlOTQ5OGNiNWRkMTQ0ODlcLzA0LWNvcHkuanBnO2h0dHBzOlwvXC9sb3ZlcnN0b29uLmNvbVwvd3AtY29udGVudFwvdXBsb2Fkc1wvV1AtbWFuZ2FcL2RhdGFcL21hbmdhXzY4YjhmYWExYzc2ODZcL2UzNDRkNjcyYTdjMDY5ZmJmZTk0OThjYjVkZDE0NDg5XC8wNS1jb3B5LmpwZztodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL3dwLWNvbnRlbnRcL3VwbG9hZHNcL1dQLW1hbmdhXC9kYXRhXC9tYW5nYV82OGI4ZmFhMWM3Njg2XC9lMzQ0ZDY3MmE3YzA2OWZiZmU5NDk4Y2I1ZGQxNDQ4OVwvMDYtY29weS5qcGc7aHR0cHM6XC9cL2xvdmVyc3Rvb24uY29tXC93cC1jb250ZW50XC91cGxvYWRzXC9XUC1tYW5nYVwvZGF0YVwvbWFuZ2FfNjhiOGZhYTFjNzY4NlwvZTM0NGQ2NzJhN2MwNjlmYmZlOTQ5OGNiNWRkMTQ0ODlcLzA3LWNvcHkuanBnO2h0dHBzOlwvXC9sb3ZlcnN0b29uLmNvbVwvd3AtY29udGVudFwvdXBsb2Fkc1wvV1AtbWFuZ2FcL2RhdGFcL21hbmdhXzY4YjhmYWExYzc2ODZcL2UzNDRkNjcyYTdjMDY5ZmJmZTk0OThjYjVkZDE0NDg5XC8wOC1jb3B5LmpwZztodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL3dwLWNvbnRlbnRcL3VwbG9hZHNcL1dQLW1hbmdhXC9kYXRhXC9tYW5nYV82OGI4ZmFhMWM3Njg2XC9lMzQ0ZDY3MmE3YzA2OWZiZmU5NDk4Y2I1ZGQxNDQ4OVwvMDktY29weS5qcGc7aHR0cHM6XC9cL2xvdmVyc3Rvb24uY29tXC93cC1jb250ZW50XC91cGxvYWRzXC9XUC1tYW5nYVwvZGF0YVwvbWFuZ2FfNjhiOGZhYTFjNzY4NlwvZTM0NGQ2NzJhN2MwNjlmYmZlOTQ5OGNiNWRkMTQ0ODlcLzEwLWNvcHkuanBnO2h0dHBzOlwvXC9sb3ZlcnN0b29uLmNvbVwvd3AtY29udGVudFwvdXBsb2Fkc1wvV1AtbWFuZ2FcL2RhdGFcL21hbmdhXzY4YjhmYWExYzc2ODZcL2UzNDRkNjcyYTdjMDY5ZmJmZTk0OThjYjVkZDE0NDg5XC8xMS1jb3B5LmpwZztodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL3dwLWNvbnRlbnRcL3VwbG9hZHNcL1dQLW1hbmdhXC9kYXRhXC9tYW5nYV82OGI4ZmFhMWM3Njg2XC9lMzQ0ZDY3MmE3YzA2OWZiZmU5NDk4Y2I1ZGQxNDQ4OVwvMTItY29weS5qcGc7aHR0cHM6XC9cL2xvdmVyc3Rvb24uY29tXC93cC1jb250ZW50XC91cGxvYWRzXC9XUC1tYW5nYVwvZGF0YVwvbWFuZ2FfNjhiOGZhYTFjNzY4NlwvZTM0NGQ2NzJhN2MwNjlmYmZlOTQ5OGNiNWRkMTQ0ODlcLzEzLWNvcHkuanBnO2h0dHBzOlwvXC9sb3ZlcnN0b29uLmNvbVwvd3AtY29udGVudFwvdXBsb2Fkc1wvV1AtbWFuZ2FcL2RhdGFcL21hbmdhXzY4YjhmYWExYzc2ODZcL2UzNDRkNjcyYTdjMDY5ZmJmZTk0OThjYjVkZDE0NDg5XC8xNC1jb3B5LmpwZztodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL3dwLWNvbnRlbnRcL3VwbG9hZHNcL1dQLW1hbmdhXC9kYXRhXC9tYW5nYV82OGI4ZmFhMWM3Njg2XC9lMzQ0ZDY3MmE3YzA2OWZiZmU5NDk4Y2I1ZGQxNDQ4OVwvOTk5XzcyMC5qcGciLCJjYyI6IiIsImJhY2siOiJodHRwczpcL1wvbG92ZXJzdG9vbi5jb21cL21hbmdhXC9zaWdyaWRcLyJ9"
    run_visible_browser_for_inspection(redirect_url)