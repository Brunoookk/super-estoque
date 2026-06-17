# SuperEstoque

Documentacao do sistema local de controle de estoque SuperEstoque.

O SuperEstoque e uma aplicacao web local com backend em Python, banco SQLite e interface em HTML/JavaScript. O sistema foi preparado para uso real na empresa: inicia sem dados de exemplo, possui login, permissoes por area, controle de itens, movimentacoes, compras, fornecedores, rastreabilidade, relatorios, favoritos, leitura por camera e exportacoes.

## Sumario

- [Visao geral](#visao-geral)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como rodar](#como-rodar)
- [Login e acessos](#login-e-acessos)
- [Primeiro uso](#primeiro-uso)
- [Modulos do sistema](#modulos-do-sistema)
- [Rotinas operacionais](#rotinas-operacionais)
- [Permissoes e usuarios](#permissoes-e-usuarios)
- [Importacao e exportacao](#importacao-e-exportacao)
- [QR Code e camera](#qr-code-e-camera)
- [Modo apresentacao e PDFs](#modo-apresentacao-e-pdfs)
- [Banco de dados e backup](#banco-de-dados-e-backup)
- [Configuracao por ambiente](#configuracao-por-ambiente)
- [Deploy no Render](#deploy-no-render)
- [Seguranca](#seguranca)
- [Solucao de problemas](#solucao-de-problemas)
- [Manutencao tecnica](#manutencao-tecnica)

## Visao geral

O SuperEstoque atende rotinas de almoxarifado, manutencao, compras, financeiro e administracao.

Principais recursos:

- Login com sessao segura.
- Perfil `chefe/admin` com acesso total.
- Usuarios por setor, como RH, Compras, Financeiro e Operacao.
- Permissoes por modulo.
- Cadastro, edicao, duplicacao, exclusao e favoritos de itens.
- Busca em tempo real com atalho `F`.
- Controle de entrada e saida.
- Bloqueio de saida maior que o saldo disponivel.
- Confirmacao dupla antes de zerar ou excluir item.
- Observacao obrigatoria em movimentacoes acima de limite configuravel.
- Repetir ultima movimentacao de um item.
- Lista de compras por ruptura ou estoque abaixo do minimo.
- Fornecedores, custos, ordens de compra e rastreabilidade por lote.
- Historico e auditoria.
- Exportacao CSV, Excel e PDF.
- QR Code por item e leitura por camera.
- Notificacoes para itens criticos.
- Modo apresentacao para reunioes.

## Estrutura do projeto

```text
superEstoque/
  backend/
    data/
      superestoque.db
    server.py
  index.html
  iniciar_superestoque.bat
  README.md
  .gitignore
```

Arquivos principais:

- `index.html`: interface completa do sistema.
- `backend/server.py`: servidor HTTP, API, login, sessoes, permissoes e SQLite.
- `backend/data/superestoque.db`: banco de dados local.
- `iniciar_superestoque.bat`: atalho para iniciar o sistema no Windows.
- `README.md`: esta documentacao.

## Como rodar

### Opcao recomendada no Windows

Execute:

```text
iniciar_superestoque.bat
```

O arquivo inicia o backend e abre o navegador automaticamente.

Endereco local:

```text
http://127.0.0.1:8000/
```

Importante: nao abra o `index.html` diretamente. Login, banco, permissoes e sincronizacao dependem do backend Python.

### Pelo terminal

No diretorio do projeto:

```powershell
python backend\server.py
```

Depois abra:

```text
http://127.0.0.1:8000/
```

### Verificacao rapida

Com o servidor rodando, acesse:

```text
http://127.0.0.1:8000/health
```

Resposta esperada:

```json
{"ok": true}
```

## Login e acessos

Usuarios iniciais:

```text
Usuario: chefe
Perfil: admin

Usuario: funcionario
Perfil: usuario comum
```

As senhas podem ser configuradas por variaveis de ambiente antes da primeira criacao do banco:

```text
SUPERESTOQUE_ADMIN_PASSWORD=sua_senha_forte
SUPERESTOQUE_EMPLOYEE_PASSWORD=sua_senha_forte
```

Se as variaveis nao forem configuradas antes da criacao do banco, o backend gera senhas automaticamente. Guarde as credenciais com seguranca.

Em deploys como Render, se o banco persistente ja existir e o login falhar, defina ou atualize `SUPERESTOQUE_ADMIN_PASSWORD` e reinicie o servico. Na inicializacao, o sistema ativa o usuario `chefe` e redefine a senha dele para o valor dessa variavel.

No banco local usado durante a preparacao deste projeto, as senhas foram redefinidas para acesso inicial operacional:

```text
chefe / chefe123
funcionario / funcionario123
```

Recomendacao: apos entrar como `chefe`, troque as senhas pela area Admin.

## Primeiro uso

O sistema inicia sem dados de exemplo.

Fluxo recomendado:

1. Entrar como `chefe`.
2. Abrir a aba `Admin`.
3. Criar usuarios reais por setor.
4. Definir permissoes por area.
5. Cadastrar fornecedores, se aplicavel.
6. Cadastrar itens manualmente ou importar CSV.
7. Configurar limite de observacao obrigatoria.
8. Comecar a registrar entradas e saidas.

## Modulos do sistema

### Dashboard

Tela inicial com visao geral do estoque.

Mostra:

- Total de itens.
- Itens sem estoque.
- Itens abaixo do minimo.
- Itens no limite.
- Itens OK.
- Valor estimado em estoque.
- Saude do estoque.
- Comparativo do mes atual vs mes anterior.
- Resumo por criticidade.

Botoes:

- `Notificacoes`: ativa notificacoes do navegador.
- `Limite observacao`: define a quantidade acima da qual a observacao vira obrigatoria.
- `Modo apresentacao`: exibe relatorios em tela cheia.
- `Exportar resumo em PDF`: gera um PDF limpo com os principais numeros.
- `Exportar CSV`: exporta estoque filtrado.
- `Exportar Excel`: exporta estoque filtrado em XLSX.
- `Importar CSV`: importa itens.
- `Ler codigo pela camera`: abre leitor de QR/codigo.

### Estoque

Tabela completa dos itens cadastrados.

Recursos:

- Busca por codigo, descricao ou local.
- Filtro por status.
- Filtro por local.
- Ordenacao clicando no cabecalho.
- Favoritar item com estrela.
- Duplicar item.
- Registrar saida.
- Repetir ultima movimentacao.
- Gerar QR Code.
- Zerar item com confirmacao dupla.
- Excluir item com confirmacao dupla.
- Exportar CSV e Excel.

Atalho:

```text
F
```

Foca diretamente no campo de busca, desde que o usuario nao esteja digitando em outro campo.

### Lista de Compras

Mostra itens com status:

- `SEM ESTOQUE`
- `COMPRAR`

Inclui:

- Quantidade atual.
- Minimo.
- Sugestao de compra.
- Tendencia.
- Botao para marcar pedido.

### Saude do Estoque

Mostra:

- Status consolidado.
- Locais com itens criticos.

### Historico

Lista movimentacoes de entrada e saida.

Filtros:

- Data inicial.
- Data final.
- Tipo de movimentacao.

Tambem permite exportar CSV filtrado.

### Relatorios

Mostra:

- Relatorio de saude.
- Top 5 itens mais movimentados.
- Grafico de movimentacoes dos ultimos 30 dias.
- Grafico de quantidade por deposito.
- Curva ABC por giro.

Botao:

- `Exportar relatorio PDF`.

### Fornecedores

Permite cadastrar fornecedores com:

- Razao social.
- CNPJ.
- Contato.
- E-mail.
- Prazo medio de entrega.
- Avaliacao de preco, prazo e qualidade.

Tambem exibe historico de compras por fornecedor.

### Ordens de Compra

Permite criar e acompanhar OCs.

Fluxo:

1. Criar OC.
2. Aprovar.
3. Enviar.
4. Receber.

Ao receber uma OC, o sistema pede lote e validade para rastreabilidade.

### Financeiro

Mostra:

- Custo por item e fornecedor.
- Valor em estoque.
- Compras por periodo.
- Comparativo de preco entre fornecedores.

### Rastreabilidade

Mostra:

- Lotes por item.
- Validade.
- Saldo por lote.
- Consumo de lotes em saidas.

### Admin

Area exclusiva para `chefe/admin`.

Permite:

- Criar usuario.
- Editar usuario.
- Redefinir senha.
- Definir setor.
- Definir perfil.
- Ativar ou desativar usuario.
- Marcar permissoes por modulo.
- Ver historico de login.
- Ver log de auditoria.

## Rotinas operacionais

### Cadastrar item

O cadastro principal de itens fica na tela `Estoque`, no formulario `Novo item`. Tambem e possivel importar itens por CSV. Campos principais:

- Codigo.
- Descricao.
- Local.
- Quantidade.
- Minimo.
- Status.
- Fornecedor.
- Custo.
- Validade/lote, quando aplicavel.

### Duplicar item

Na tabela de estoque:

1. Clique em `Duplicar`.
2. Informe o novo codigo.
3. Confirme ou ajuste a descricao.

A copia nasce com quantidade `0`, status `SEM ESTOQUE` e sem favorito.

### Favoritar item

Na tabela de estoque:

1. Clique na estrela do item.
2. Itens favoritos ficam fixados no topo da lista.

### Registrar saida

Na tabela de estoque:

1. Clique em `Registrar saida`.
2. Informe tipo, quantidade, responsavel e observacao.
3. Se a quantidade for maior que o saldo, a saida sera bloqueada.
4. Se a quantidade passar do limite configurado, a observacao sera obrigatoria.

### Repetir ultima movimentacao

Na tabela de estoque:

1. Clique em `Repetir`.
2. O sistema usa os dados da ultima movimentacao do item como preenchimento inicial.
3. Revise os dados antes de confirmar.

### Zerar item

Na tabela de estoque:

1. Clique em `Zerar`.
2. Leia a confirmacao.
3. Clique em `Estou ciente`.
4. Clique em `Confirmar definitivamente`.

O sistema registra uma movimentacao de ajuste e deixa o saldo em zero.

### Excluir item

Na tabela de estoque:

1. Clique em `Excluir`.
2. Leia a confirmacao.
3. Clique em `Estou ciente`.
4. Clique em `Confirmar definitivamente`.

A exclusao remove o cadastro da lista local. O historico ja registrado permanece.

## Permissoes e usuarios

Permissoes disponiveis:

```text
dashboard
estoque
compras
historico
fornecedores
saude
relatorios
financeiro
rastreabilidade
ocs
admin
```

Perfis:

- `admin`: acesso total, usado pelo chefe.
- `employee`: usuario comum, com permissoes marcadas individualmente.

Exemplo de usuario RH:

```text
Usuario: rh
Setor: RH
Perfil: Usuario
Permissoes: dashboard, relatorios, historico
```

Exemplo de usuario Compras:

```text
Usuario: compras
Setor: Compras
Perfil: Usuario
Permissoes: dashboard, compras, fornecedores, ocs, financeiro
```

## Importacao e exportacao

### Importar CSV

Use o botao `Importar CSV`.

Formato esperado:

```csv
Codigo,Descricao,Local,Qtd,Minimo,Status
ABC-001,Item de exemplo,Almoxarifado,10,2,OK
```

Observacoes:

- Codigos repetidos atualizam o item existente.
- Codigos novos criam itens.
- O sistema inicia sem dados de exemplo.

### Exportar CSV

Exporta a lista filtrada com dados principais.

### Exportar Excel

Exporta a lista filtrada em `.xlsx`.

### Exportar PDF

Disponivel em:

- Dashboard: `Exportar resumo em PDF`.
- Relatorios: `Exportar relatorio PDF`.
- OCs: botao `PDF` por ordem de compra.

## QR Code e camera

### Gerar QR Code

Na tabela de estoque:

1. Clique em `QR`.
2. O sistema gera um QR Code contendo os dados principais do item.

### Ler pela camera

No Dashboard:

1. Clique em `Ler codigo pela camera`.
2. Permita acesso a camera no navegador.
3. Aponte para o QR Code.
4. O sistema filtra o item lido.

Observacao: em alguns navegadores, camera exige acesso via `http://127.0.0.1` ou HTTPS.

## Modo apresentacao e PDFs

### Modo apresentacao

Use o botao `Modo apresentacao` no Dashboard.

O sistema:

- Entra em tela cheia.
- Mostra area de relatorios.
- Esconde controles operacionais.
- Mantem graficos e numeros visiveis.

Para sair:

```text
Sair apresentacao
```

### Comparativo mensal

Os KPIs do Dashboard mostram indicador:

```text
subiu
caiu
igual
```

O comparativo usa movimentacoes do mes atual contra o mes anterior.

## Banco de dados e backup

Banco padrao:

```text
backend/data/superestoque.db
```

Backup manual simples:

1. Feche o sistema ou pare o backend.
2. Copie o arquivo `backend/data/superestoque.db`.
3. Guarde a copia com data.

Exemplo:

```text
superestoque-2026-06-17.db
```

Restauracao:

1. Pare o backend.
2. Substitua `backend/data/superestoque.db` pela copia desejada.
3. Inicie o sistema novamente.

Arquivos de backup ja criados durante manutencoes:

```text
backend/data/superestoque.db.bak-login-reset
backend/data/superestoque.db.bak-before-production-clean
```

## Configuracao por ambiente

Variaveis aceitas:

```text
SUPERESTOQUE_HOST
SUPERESTOQUE_PORT
SUPERESTOQUE_DATA_DIR
SUPERESTOQUE_ADMIN_PASSWORD
SUPERESTOQUE_EMPLOYEE_PASSWORD
PORT
```

Uso:

- `SUPERESTOQUE_HOST`: host do servidor.
- `SUPERESTOQUE_PORT`: porta local.
- `SUPERESTOQUE_DATA_DIR`: pasta do banco SQLite.
- `SUPERESTOQUE_ADMIN_PASSWORD`: senha inicial do chefe.
- `SUPERESTOQUE_EMPLOYEE_PASSWORD`: senha inicial do funcionario.
- `PORT`: usado em hospedagens como Render.

Padrao local:

```text
Host: 127.0.0.1
Porta: 8000
Banco: backend/data/superestoque.db
```

O arquivo `iniciar_superestoque.bat` usa:

```text
SUPERESTOQUE_HOST=0.0.0.0
```

Isso permite acesso por outros dispositivos na mesma rede.

## Acesso pelo celular na mesma rede

1. Conecte o computador e o celular na mesma rede Wi-Fi.
2. Execute:

```text
iniciar_superestoque.bat
```

3. Na janela do backend, procure:

```text
Acesso no celular: http://SEU-IP:8000
```

4. Abra esse endereco no celular.

Se nao abrir:

- Verifique se ambos estao na mesma rede.
- Permita o acesso no firewall do Windows em rede privada.
- Confira se antivirus/firewall nao bloqueou a porta `8000`.

## Deploy no Render

1. Suba o repositorio no GitHub.
2. No Render, clique em `New > Web Service`.
3. Conecte o repositorio.
4. Configure:

```text
Name: super-estoque
Branch: main
Runtime: Python
Build Command: python --version
Start Command: python backend/server.py
```

5. Configure:

```text
Health Check Path: /health
```

6. Para persistir banco SQLite, adicione Persistent Disk:

```text
Mount Path: /var/data
Environment Variable:
SUPERESTOQUE_DATA_DIR=/var/data
```

Sem disco persistente, os dados podem ser perdidos quando o Render recriar o servico.

Para evitar falha de login no Render, configure tambem as variaveis de ambiente:

```text
SUPERESTOQUE_ADMIN_PASSWORD=sua_senha_forte
SUPERESTOQUE_EMPLOYEE_PASSWORD=sua_senha_funcionario
```

Depois salve as variaveis e reinicie/redeploy o servico. O usuario `chefe` sera ativado e tera a senha sincronizada com `SUPERESTOQUE_ADMIN_PASSWORD`.

## Seguranca

Implementado:

- Senhas com PBKDF2 + salt.
- Cookie de sessao `HttpOnly`.
- Cookie com `SameSite=Strict`.
- Token CSRF para operacoes de escrita.
- Separacao de permissoes por usuario.
- Bloqueio de saida acima do estoque.
- Confirmacao dupla para zerar/excluir.
- Sessoes com duracao de 8 horas.

Boas praticas:

- Trocar senhas iniciais.
- Criar usuarios individuais.
- Nao compartilhar login do chefe.
- Fazer backup regular do banco.
- Restringir acesso por rede quando usado em ambiente interno.
- Usar HTTPS em ambiente publicado.

## API interna

Rotas principais:

```text
GET    /
GET    /health
GET    /api/me
POST   /api/login
POST   /api/logout
GET    /api/items
POST   /api/items
PUT    /api/items/{id}
DELETE /api/items/{id}
GET    /api/movements
POST   /api/movements
GET    /api/sync
GET    /api/admin/users
POST   /api/admin/users
PUT    /api/admin/users/{id}
DELETE /api/admin/users/{id}
```

Observacao: as rotas de escrita exigem usuario logado e token CSRF.

## Solucao de problemas

### Nao consigo logar

Verifique:

- Se abriu por `http://127.0.0.1:8000/`.
- Se o backend esta rodando.
- Se a senha esta correta.
- Se o usuario esta ativo no Admin.

Teste de saude:

```text
http://127.0.0.1:8000/health
```

### A tela mostra dados antigos

Use:

```text
Ctrl + F5
```

Se necessario, limpe dados do site no navegador. O sistema usa `localStorage` para parte das informacoes da interface.

### Camera nao abre

Possiveis causas:

- Permissao negada no navegador.
- Navegador bloqueando camera.
- Acesso fora de contexto permitido.
- Dispositivo sem camera disponivel.

Tente:

- Usar Chrome ou Edge.
- Permitir camera.
- Abrir por `http://127.0.0.1:8000/`.

### Excel nao exporta

O Excel depende da biblioteca SheetJS carregada por CDN.

Verifique:

- Internet disponivel.
- Bloqueio de rede/firewall.
- Console do navegador.

### PDF nao exporta

O PDF depende da biblioteca jsPDF carregada por CDN.

Verifique:

- Internet disponivel.
- Bloqueio de rede/firewall.
- Permissao de download do navegador.

### Celular nao acessa

Verifique:

- Mesmo Wi-Fi.
- Firewall liberado.
- IP correto mostrado no backend.
- Porta `8000` livre.

### Porta 8000 ocupada

Feche a janela antiga do backend ou altere:

```text
SUPERESTOQUE_PORT=8001
```

## Manutencao tecnica

### Validar sintaxe do backend

```powershell
python -c "import ast, pathlib; ast.parse(pathlib.Path('backend/server.py').read_text(encoding='utf-8-sig')); print('backend syntax OK')"
```

### Validar sintaxe do JavaScript embutido

```powershell
node -e "const fs=require('fs'),vm=require('vm'); const html=fs.readFileSync('index.html','utf8'); const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).filter(s=>s.trim()); scripts.forEach((s,i)=>new vm.Script(s,{filename:'inline-'+i+'.js'})); console.log('inline JS syntax OK:', scripts.length);"
```

### Verificar usuarios no banco

```powershell
python -c "import sqlite3; conn=sqlite3.connect(r'backend\data\superestoque.db'); print(conn.execute('select username, role, active from users').fetchall())"
```

### Limpar dados de estoque com cuidado

Antes de qualquer limpeza:

1. Pare o backend.
2. Faca backup de `backend/data/superestoque.db`.
3. Execute comandos SQL somente se tiver certeza.

Nunca apague o banco sem backup.

## Observacoes importantes

- O sistema nao deve ser operado abrindo o HTML direto.
- O banco SQLite e arquivo unico; proteja esse arquivo.
- Algumas funcionalidades de exportacao dependem de bibliotecas externas via CDN.
- O sistema local e ideal para uso interno, rede local e pequenos deployments.
- Para uso publico, configure HTTPS, senhas fortes e disco persistente.
