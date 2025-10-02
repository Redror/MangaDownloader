import re
import base64

def sanitize_foldername(name):
    """Remove caracteres inválidos de um nome de arquivo/pasta."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_image_with_selenium(driver, image_url, save_path):
    """
    Usa o Selenium para baixar uma imagem executando um script JavaScript e
    verifica se o conteúdo retornado é realmente uma imagem antes de salvar.
    """
    try:
        # Script JavaScript que busca a imagem como um blob e a converte para Base64
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
            # Isso acontecerá se a URL der um erro de rede (como 404 Not Found)
            return False

        # Decodifica a string Base64 para dados de imagem binários
        header, encoded = base64_data.split(",", 1)
        
        # >>> NOVA VERIFICAÇÃO <<<
        # Se o cabeçalho não indicar que o conteúdo é uma imagem, retorna falha.
        # Isso impede que páginas de erro XML (como a que você encontrou) sejam salvas.
        if not header.startswith('data:image'):
            #print(f"    -> Conteúdo recebido de {image_url} não é uma imagem. Pulando.")
            return False
            
        image_data = base64.b64decode(encoded)
        
        # Salva os dados binários no arquivo
        with open(save_path, 'wb') as f:
            f.write(image_data)
        return True
        
    except Exception:
        # Se qualquer erro ocorrer (ex: a URL não existe e o JS falha),
        # a função retornará False, contando como uma falha de download.
        return False