import re
import base64

def sanitize_foldername(name):
    """Remove caracteres inválidos de um nome de arquivo/pasta."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_image_with_selenium(driver, image_url, save_path):
    """
    Usa o Selenium para baixar uma imagem executando um script JavaScript.
    """
    try:
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
            print(f"    -> Falha ao obter dados da imagem (retorno nulo do JS) para: {image_url}")
            return False

        header, encoded = base64_data.split(",", 1)
        image_data = base64.b64decode(encoded)
        
        with open(save_path, 'wb') as f:
            f.write(image_data)
        return True
        
    except Exception as e:
        print(f"    -> Erro na função download_image_with_selenium para '{image_url}': {e}")
        return False