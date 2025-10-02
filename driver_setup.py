import time
import undetected_chromedriver as uc

def setup_selenium_driver(run_headless=True):
    """
    Configura e retorna uma instância do driver, com patches para evitar detecção.
    """
    print("Iniciando o navegador")
    
    options = uc.ChromeOptions()
    
    logging_prefs = {'performance': 'ALL'}
    options.set_capability('goog:loggingPrefs', logging_prefs)
    
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
            print("    -> Janela do navegador foi minimizada.")
        
        # Script para burlar detecções de bot mais avançadas
        script = """
            // Remove a propriedade 'webdriver' do navigator, a principal forma de detecção
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });

            // Bloqueia a detecção de devtools que alguns sites usam
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
        
        # Injeta o script para ser executado em cada novo documento/página
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": script
        })

    except Exception as e:
        print(f"!!! ERRO ao iniciar o undetected-chromedriver: {e}")
        print("!!! Verifique se o Google Chrome está instalado e tente novamente.")
        return None
        
    return driver