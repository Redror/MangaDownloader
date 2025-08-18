# Manga Downloader

## 📖 O que este programa faz?

**Manga Downloader** é uma ferramenta de linha de comando que automatiza o download de capítulos de mangás e webtoons diretamente de sites suportados. Você fornece a URL da página principal da obra, e o programa baixa as imagens, organizando-as em pastas por capítulo.

## ⚠️ Requisito Obrigatório

Para que o programa funcione, **é essencial que você tenha o navegador Google Chrome instalado** no seu computador.

O script usa o Chrome em segundo plano (de forma invisível) para navegar nas páginas e encontrar as imagens dos capítulos, simulando o acesso de um usuário real para contornar proteções.

## ✅ Sites Suportados

Atualmente, o downloader é compatível com os seguintes sites:
* `sussytoons`
* `mangalivre`
* `sakuramangas`

## 🚀 Como Usar (Guia Rápido)

#### Passo 1: Execute o programa
Dê um duplo clique no arquivo `MangaDownloader.exe`. Uma janela de terminal preta irá se abrir.

#### Passo 2: Copie a URL da obra
No seu navegador, acesse um dos sites suportados e vá para a **página principal do mangá** que você deseja baixar. Copie a URL da barra de endereços (o link completo).

#### Passo 3: Cole a URL no programa
Clique na janela do terminal e cole a URL que você copiou. Pressione **Enter**.

#### Passo 4: Escolha os capítulos
O programa irá analisar a página e listar quantos capítulos encontrou. Em seguida, ele perguntará o que você deseja baixar:
* Digite **1** para baixar **todos os capítulos**.
* Digite **2** para escolher um **intervalo específico** (ex: do capítulo 10 ao 20).

#### Passo 5: Aguarde o download
O programa começará a baixar as imagens. Ele criará uma nova pasta com o nome do mangá no mesmo local onde o `.exe` está. Dentro dela, cada capítulo será salvo em sua própria subpasta.

---

## ⚠️ Solução de Problemas

* **Primeira Execução Lenta:** Na primeira vez que você rodar o programa, ele pode demorar um pouco para iniciar. Isso ocorre porque ele está baixando o "driver" correto para controlar o seu Google Chrome. É um processo automático e só acontece uma vez.

* **Aviso "O Windows protegeu o computador":** Se você vir uma tela azul do Windows SmartScreen, isso é um aviso de segurança padrão.
    1.  Clique em **"Mais informações"**.
    2.  Depois, clique no botão **"Executar mesmo assim"**.

* **Erros ou Falhas no Download:** Falhas podem ocorrer por instabilidade na sua internet ou no site do mangá. Se um capítulo falhar, você pode tentar rodar o programa novamente escolhendo apenas o intervalo daquele capítulo específico.
