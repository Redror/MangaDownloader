from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def setup_selenium_driver(run_headless=True):
    """
    Configura e retorna uma instância do driver, usando o Selenium Manager
    para baixar o driver correto automaticamente.
    """
    print("Iniciando o navegador com Selenium Manager...")

    options = Options()

    if run_headless:
        print(" -> Rodando em modo Headless (invisível).")
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
    else:
        print(" -> Rodando em modo visível.")

    options.add_argument('--log-level=3')
    # Esta opção desativa a mensagem "DevTools listening on..." no console
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        # O Selenium Manager é chamado automaticamente aqui ao não especificar um path no Service
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)

        if not run_headless:
            driver.maximize_window()
            driver.minimize_window()
            print("    -> Janela do navegador foi minimizada.")

        # O script para bloquear o anti-devtools pode ser mantido
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                const originalSetInterval = window.setInterval;
                window.setInterval = (handler, timeout, ...args) => {
                    const handlerStr = handler.toString();
                    if (handlerStr.includes('isSuspend') && handlerStr.includes('detect')) {
                        console.log('Timer do DisableDevtool bloqueado.');
                        return null;
                    }
                    return originalSetInterval(handler, timeout, ...args);
                };
            """
        })

    except Exception as e:
        print(f"!!! ERRO ao iniciar o Selenium: {e}")
        print("!!! Verifique se o Google Chrome está instalado e tente novamente.")
        return None

    return driver
