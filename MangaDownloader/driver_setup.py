import undetected_chromedriver as uc

def setup_selenium_driver(run_headless=True):
    """
    Configura e retorna uma instância do driver, aceitando um parâmetro
    para rodar em modo headless (invisível) ou visível.
    """
    print("Iniciando o navegador")
    
    options = uc.ChromeOptions()
    
    if run_headless:
        print(" -> Rodando em modo Headless (invisível).")
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
    else:
        print(" -> Rodando em modo visível (necessário para este site).")

    options.add_argument('--log-level=3')

    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        
        if not run_headless:
            driver.maximize_window()
            driver.minimize_window()
            print("    -> Janela do navegador foi minimizada.")
        
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
        print(f"!!! ERRO ao iniciar o undetected-chromedriver: {e}")
        print("!!! Verifique se o Google Chrome está instalado e tente novamente.")
        return None
        
    return driver