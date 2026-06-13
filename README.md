# SuperEstoque

Sistema local de controle de estoque com backend Python/SQLite, login de funcionarios, area administrativa para chefe e sincronizacao automatica entre telas.

## Como rodar

Opcao mais simples no Windows:

```text
iniciar_superestoque.bat
```

Ou pelo terminal:

```powershell
python backend\server.py
```

Depois abra:

```text
http://127.0.0.1:8000/
```

Nao abra o HTML direto. Login, banco, seguranca e sincronizacao dependem do backend.

## Acessos iniciais

```text
Chefe/Admin: chefe / admin123
Funcionario: funcionario / func123
```

Troque essas senhas pela tela de Administracao antes de usar em producao.

## O que esta funcional

- Login com sessao.
- Perfil Funcionario e Chefe/Admin.
- Tela administrativa para criar, editar perfil, redefinir senha e desativar usuarios.
- Cadastro, edicao e exclusao de itens.
- Exclusao de itens restrita ao chefe/admin.
- Registro de entrada e saida de estoque.
- Historico de movimentacoes.
- Lista de compras por ruptura ou quantidade abaixo do minimo.
- Exportacao CSV.
- Etiquetas.
- Sincronizacao automatica a cada 4 segundos e ao focar a aba.

## Seguranca implementada

- Senhas com PBKDF2 + salt.
- Cookie de sessao `HttpOnly` e `SameSite=Strict`.
- Token CSRF nas operacoes de escrita.
- Separacao de permissoes por perfil.
- Banco SQLite local em `backend/data/superestoque.db`.
