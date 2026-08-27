# Serra Loterias — versão com sincronização automática

Esta versão mantém a identidade visual da V8 e transforma **Bolões disponíveis**
em conteúdo lido de `data/boloes.json`.

## Como funciona
1. O GitHub Actions abre, com navegador automático, a página pública:
   https://loteriasonline.caixa.gov.br/silce-web/#/bolao-caixa/20002
2. Confirma a tela de maioridade quando necessário.
3. Lê os bolões visíveis da página da Serra Loterias.
4. Atualiza `data/boloes.json`.
5. O site lê esse arquivo e redesenha os cards automaticamente.
6. O processo roda **a cada hora** e também pode ser executado manualmente.

## Segurança / comportamento
- Não usa CPF, senha ou login.
- Só consulta a página pública do Marketplace.
- Se a CAIXA mudar o HTML ou bloquear automação, o site não inventa bolões:
  mostra um botão para consultar diretamente a CAIXA.
- O script guarda `data/ultima_pagina.txt` para facilitar ajustes se o layout da CAIXA mudar.

## Publicação recomendada
Hospedar este pacote em um repositório GitHub com GitHub Pages habilitado.
A ação programada atualiza o JSON e o Pages publica a nova versão.

## Observação importante
A CAIXA não oferece, nas fontes públicas que conseguimos confirmar, uma API
documentada especificamente para terceiros sincronizarem os bolões de uma lotérica.
Por isso esta versão usa leitura automatizada da página pública. Ela é mais frágil
que uma API oficial e pode precisar de ajuste se a CAIXA alterar o site.
