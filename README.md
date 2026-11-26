# SIGMA — Sistema Interno de Gestão de Material Armazenado

Controle de estoque de materiais e produtos para uma pequena empresa têxtil.
Disciplina de Desenvolvimento Web — IFES, turma 2024/2, grupo G3.

## Integrantes
- Halisson Julio
- João Vitor Scheidegger
- Luiz Henrique Batista
- Rafael Marques

## Tecnologias
Python 3.10+, Flask, Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-WTF (CSRF), SQLite, Bootstrap 5 e Bootstrap Icons.

## Instalação

### Windows (PowerShell)
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
Se o PowerShell bloquear a ativação, rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ou use o `cmd` com `.venv\Scripts\activate.bat`.

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` e troque a `SECRET_KEY`. Para gerar uma chave:
`python -c "import secrets; print(secrets.token_hex(32))"`

## Criar o banco de dados
```bash
flask db upgrade   # cria as tabelas a partir das migrations
flask seed         # opcional: dados de exemplo
```

## Executar
```bash
flask run
```
Acesse http://127.0.0.1:5000

## Estrutura (MVC)
- `models/`: acesso ao SQLite (SQLAlchemy), validações e regras de negócio
- `controllers/`: Blueprints do Flask; recebem a requisição, chamam o Model e devolvem a View
- `templates/` e `static/`: Views (Jinja2 + Bootstrap 5)

## Regras de negócio implementadas
| Regra | Onde |
|---|---|
| RN01: saldo nunca negativo | `Movimentacao.registrar` + CHECK no banco |
| RN02: campos obrigatórios | `validar()` de cada Model |
| RN03: movimentações definitivas | sem rotas de exclusão + listener que bloqueia delete/update |
| RN04: saldo só muda por movimentação | quantidade fora de `CAMPOS_PERMITIDOS` |
| RN05: alerta quando saldo ≤ mínimo | `ItemEstoque.em_alerta` e dashboard |
| RN06: item com movimentação é inativado | `ItemEstoque.excluir_ou_inativar` |

## Segurança e correspondência com o barema
| Barema (CI4) | SIGMA (Flask) |
|---|---|
| filtro csrf + `csrf_field()` | `CSRFProtect` global + `csrf_token()` em todo formulário |
| `esc()` | autoescape do Jinja2 (nenhum `|safe` no projeto) |
| `allowedFields` | `CAMPOS_PERMITIDOS` em cada Model |
| `(:num)` | `<int:item_id>` |
| POST em ações que alteram dados | salvar, atualizar, excluir, reativar e registrar são POST |
| credenciais no `.env` | `SECRET_KEY` só no `.env` (fora do Git) |
| migrations e seeders | Flask-Migrate (`flask db upgrade`) e `flask seed` |
