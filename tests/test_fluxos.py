import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from sqlalchemy import text
from werkzeug.datastructures import MultiDict

from app import create_app
from config import Config
from models import ItemEstoque, Material, Movimentacao, Produto, db
from models.usuario import Usuario


class FluxosTest(unittest.TestCase):
    def setUp(self):
        pasta = TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        configuracao = type("ConfigTeste", (Config,), {
            "TESTING": True,
            "SECRET_KEY": "chave exclusiva para o banco de teste",
            "SESSION_COOKIE_SECURE": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{Path(pasta.name) / 'teste.db'}",
        })
        self.app = create_app(configuracao)

    def comando(self, *args, entrada=None):
        resposta = self.app.test_cli_runner().invoke(args=list(args), input=entrada)
        self.assertEqual(resposta.exit_code, 0, resposta.output or str(resposta.exception))

    def post(self, cliente, url, dados, pagina_token):
        html = cliente.get(pagina_token).get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', html)
        self.assertIsNotNone(token)
        return cliente.post(url, data={**dados, "csrf_token": token.group(1)})

    def entrar(self, cliente, login, senha):
        return self.post(cliente, "/login", {"login": login, "senha": senha}, "/login")

    def trocar_senha(self, cliente, atual, nova):
        return self.post(cliente, "/conta/senha", {
            "senha_atual": atual, "senha": nova, "confirmacao": nova,
        }, "/conta/senha")

    def test_configuracao_local_do_primeiro_admin(self):
        self.comando("db", "upgrade")
        rota = "/configuracao-inicial"
        primeiro = self.app.test_client()
        segundo = self.app.test_client()
        tela = primeiro.get("/", follow_redirects=True)
        self.assertEqual(tela.request.path, rota)
        self.assertIn("Configuração inicial", tela.get_data(as_text=True))
        segunda_tela = segundo.get(rota).get_data(as_text=True)
        segundo_token = re.search(r'name="csrf_token" value="([^"]+)"', segunda_tela).group(1)

        remoto = {"REMOTE_ADDR": "192.0.2.10"}
        self.assertEqual(segundo.get(rota, environ_overrides=remoto).status_code, 403)
        self.assertEqual(segundo.get(rota, headers={"Host": "sigma.exemplo"}).status_code, 403)
        self.assertEqual(segundo.get(rota, headers={"X-Forwarded-For": "192.0.2.10"}).status_code, 403)
        senha = "Sigm@246"
        dados = {"senha": senha, "confirmacao": senha}
        self.assertEqual(segundo.post(
            rota, data={**dados, "csrf_token": segundo_token}, environ_overrides=remoto,
        ).status_code, 403)
        self.assertEqual(self.post(
            primeiro, rota, {**dados, "confirmacao": "diferente"}, rota,
        ).status_code, 400)
        curta = self.post(primeiro, rota, {"senha": senha[:-1], "confirmacao": senha[:-1]}, rota)
        self.assertEqual(curta.status_code, 400)
        self.assertIn("pelo menos 8 caracteres", curta.get_data(as_text=True))

        resultado = self.post(primeiro, rota, dados, rota)
        self.assertEqual(resultado.status_code, 302)
        self.assertEqual(primeiro.get("/admin/funcionarios").status_code, 200)
        self.assertIn("Entrar no SIGMA", segundo.get("/", follow_redirects=True).get_data(as_text=True))
        self.assertTrue(segundo.post(rota, data={
            "senha": "senha alternativa longa", "confirmacao": "senha alternativa longa",
            "csrf_token": segundo_token,
        }).location.endswith("/login"))

        with self.app.app_context():
            conta = Usuario.query.one()
            self.assertEqual((conta.login, conta.perfil), ("admin", "admin"))
            self.assertTrue(conta.senha_hash.startswith("$argon2id$"))
            self.assertTrue(Usuario.verificar_senha(conta, senha))

    def test_criacao_inicial_simultanea(self):
        self.comando("db", "upgrade")
        barreira = Barrier(2, timeout=5)

        def criar(login):
            with self.app.app_context():
                barreira.wait()
                return Usuario.criar_primeiro_administrador(login, "senha concorrente de teste")

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(criar, ("admin", "administrador")))
        self.assertEqual(sorted(resultados), [False, True])
        with self.app.app_context():
            self.assertEqual(Usuario.query.count(), 1)

    def test_acesso_e_gerenciamento(self):
        self.comando("db", "upgrade")
        senha_admin = "senha de teste para administrador"
        self.comando("criar-admin", "admin", entrada=f"{senha_admin}\n{senha_admin}\n")
        anonimo = self.app.test_client()
        self.assertTrue(anonimo.get("/").location.endswith("/login"))
        self.assertTrue(anonimo.post("/materiais/salvar").location.endswith("/login"))

        admin = self.app.test_client()
        self.assertEqual(self.entrar(admin, "admin", senha_admin).status_code, 302)
        self.assertIn("Ainda não há itens", admin.get("/").get_data(as_text=True))
        for url, mensagem in (
            ("/materiais", "Nenhum material encontrado"),
            ("/produtos", "Nenhum produto encontrado"),
            ("/movimentacoes", "Nenhuma movimentação encontrada"),
        ):
            self.assertIn(mensagem, admin.get(url).get_data(as_text=True))
        self.assertEqual(self.post(
            admin, "/admin/funcionarios", {"login": "funcionario1", "senha": "temporaria de teste 1"},
            "/admin/funcionarios",
        ).status_code, 302)
        self.post(admin, "/admin/funcionarios", {
            "login": "funcionario2", "senha": "temporaria de teste 2",
        }, "/admin/funcionarios")

        clientes = []
        for numero in (1, 2):
            cliente = self.app.test_client()
            clientes.append(cliente)
            resposta = self.entrar(cliente, f"funcionario{numero}", f"temporaria de teste {numero}")
            self.assertTrue(resposta.location.endswith("/conta/senha"))
            self.assertTrue(cliente.get("/produtos").location.endswith("/conta/senha"))
            self.trocar_senha(cliente, f"temporaria de teste {numero}", f"nova senha de teste {numero}")
            self.assertEqual(cliente.get("/produtos").status_code, 200)
            self.assertEqual(cliente.get("/admin/funcionarios").status_code, 403)
            self.assertEqual(self.post(
                cliente, "/admin/funcionarios", {}, "/produtos",
            ).status_code, 403)

        with self.app.app_context():
            contas = Usuario.query.order_by(Usuario.login).all()
            self.assertEqual(len(contas), 3)
            self.assertTrue(all(conta.senha_hash.startswith("$argon2id$") for conta in contas))
            primeiro, segundo = contas[1].id, contas[2].id

        funcionario = clientes[0]
        nome = '<img src="exemplo">'
        self.post(funcionario, "/produtos/salvar", {
            "nome": nome, "genero": "Feminino", "categoria": "Infantil", "tamanho": "P",
            "unidade_medida": "un", "estoque_minimo": "2", "estoque_medio": "4",
            "estoque_maximo": "8", "quantidade_inicial": "3",
        }, "/produtos/novo")
        lista = funcionario.get("/produtos").get_data(as_text=True)
        self.assertNotIn(nome, lista)
        self.assertIn("&lt;img", lista)
        self.assertIn("Abaixo do estoque médio", lista)
        self.assertIn("Infantil", lista)
        self.assertIn("Feminino", lista)
        self.assertIn("Cadastrado em", lista)
        self.assertIn("Abaixo do estoque médio", clientes[1].get("/").get_data(as_text=True))

        with self.app.app_context():
            produto_id = Produto.query.one().id
        ontem = date.today() - timedelta(days=1)
        movimento = self.post(clientes[1], "/movimentacoes/registrar", {
            "tipo": "ENTRADA", "data": ontem.isoformat(), "item_id": produto_id,
            "quantidade": "6",
        }, "/movimentacoes/nova")
        self.assertEqual(movimento.status_code, 302)
        self.assertIn("Acima do máximo", funcionario.get("/produtos").get_data(as_text=True))
        historico = funcionario.get(
            f"/movimentacoes?data_inicio={ontem.isoformat()}&data_fim={ontem.isoformat()}"
        ).get_data(as_text=True)
        self.assertIn("Registrada em", historico)
        self.assertIn(ontem.strftime("%d/%m/%Y"), historico)
        self.assertIn(date.today().strftime("%d/%m/%Y"), historico)

        self.post(admin, f"/admin/funcionarios/{primeiro}/senha", {
            "senha": "senha temporaria redefinida",
        }, "/admin/funcionarios")
        self.assertTrue(funcionario.get("/produtos").location.endswith("/login"))
        self.assertTrue(
            self.entrar(funcionario, "funcionario1", "senha temporaria redefinida")
            .location.endswith("/conta/senha")
        )
        self.post(admin, f"/admin/funcionarios/{segundo}/status", {"ativo": "0"}, "/admin/funcionarios")
        self.post(admin, f"/admin/funcionarios/{segundo}/status", {"ativo": "1"}, "/admin/funcionarios")
        self.assertTrue(clientes[1].get("/produtos").location.endswith("/login"))
        self.post(admin, "/sair", {}, "/")
        self.assertTrue(admin.get("/admin/funcionarios").location.endswith("/login"))

    def test_migracao_preserva_itens_antigos(self):
        self.comando("db", "upgrade", "33df4ef26411")
        with self.app.app_context():
            db.session.execute(text("""
                INSERT INTO itens_estoque
                    (id, tipo, nome, unidade_medida, estoque_minimo, quantidade, ativo, criado_em, atualizado_em)
                VALUES (1, 'produto', 'Vestido', 'un', 1, 2, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))
            db.session.execute(text("INSERT INTO produtos VALUES (1, 'Infantil', 'P')"))
            db.session.execute(text("""
                INSERT INTO movimentacoes (id, tipo, data, criado_em)
                VALUES (1, 'ENTRADA', '2020-01-01', CURRENT_TIMESTAMP)
            """))
            db.session.execute(text("INSERT INTO itens_movimentados VALUES (1, 1, 1, 2)"))
            db.session.commit()

        self.comando("db", "upgrade")
        with self.app.app_context():
            produto = db.session.get(Produto, 1)
            self.assertEqual((produto.categoria, produto.genero), ("Infantil", None))
            self.assertEqual(produto.quantidade, 2)
            self.assertIsNone(produto.estoque_maximo)
            self.assertEqual(db.session.get(Movimentacao, 1).itens[0].item_id, produto.id)
            self.assertEqual(db.session.execute(text("PRAGMA foreign_key_check")).all(), [])

    def test_seletor_de_movimentacao_preserva_itens(self):
        self.comando("db", "upgrade")
        senha = "senha de teste do seletor"
        self.comando("criar-admin", "admin", entrada=f"{senha}\n{senha}\n")
        dados = {"unidade_medida": "un", "estoque_minimo": "0"}
        with self.app.app_context():
            material, erros = Material.criar({
                **dados, "nome": "Algodão", "cor": "Azul", "composicao": "100% algodão",
            })
            self.assertFalse(erros)
            produto, erros = Produto.criar({
                **dados, "nome": "Camiseta", "tamanho": "P", "genero": "Unissex",
            })
            self.assertFalse(erros)
            material_id, produto_id = material.id, produto.id

        cliente = self.app.test_client()
        self.entrar(cliente, "admin", senha)
        pagina = cliente.get(f"/movimentacoes/nova?item_id={produto_id}").get_data(as_text=True)
        self.assertIn('id="buscaSeletorItens"', pagina)
        self.assertIn(f'name="item_id" value="{produto_id}"', pagina)
        material_painel, produto_painel = pagina.split('id="painel-material"', 1)[1].split(
            'id="painel-produto"', 1
        )
        self.assertIn(f'data-item-id="{material_id}"', material_painel)
        self.assertNotIn(f'data-item-id="{produto_id}"', material_painel)
        self.assertIn(f'data-item-id="{produto_id}"', produto_painel)
        self.assertNotIn(f'data-item-id="{material_id}"', produto_painel)

        dados_movimentacao = {
            "tipo": "ENTRADA", "data": date.today().isoformat(), "item_id": [material_id, produto_id],
        }
        invalida = self.post(cliente, "/movimentacoes/registrar", {
            **dados_movimentacao, "quantidade": ["3", "0"],
        }, "/movimentacoes/nova")
        formulario = invalida.get_data(as_text=True)
        self.assertIn(f'name="item_id" value="{material_id}"', formulario)
        self.assertIn(f'name="item_id" value="{produto_id}"', formulario)
        self.assertIn('value="3" placeholder="0"', formulario)
        self.assertEqual(self.post(cliente, "/movimentacoes/registrar", {
            **dados_movimentacao, "quantidade": ["3", "2"],
        }, "/movimentacoes/nova").status_code, 302)
        with self.app.app_context():
            linhas = Movimentacao.query.one().itens
            self.assertEqual({linha.item_id: linha.quantidade for linha in linhas}, {
                material_id: Decimal("3"), produto_id: Decimal("2"),
            })

    def test_saldo_simultaneo_e_transacao(self):
        self.comando("db", "upgrade")
        with self.app.app_context():
            dados = {"composicao": "Algodão", "unidade_medida": "m", "estoque_minimo": "2",
                     "estoque_medio": "5", "estoque_maximo": "10"}
            primeiro, erros = Material.criar({**dados, "nome": "Malha", "quantidade_inicial": "10"})
            self.assertFalse(erros)
            segundo, erros = Material.criar({**dados, "nome": "Linha", "quantidade_inicial": "2"})
            self.assertFalse(erros)
            ids = (primeiro.id, segundo.id)
            self.assertFalse(primeiro.acima_do_maximo)
            self.assertTrue(segundo.em_alerta)
            self.assertIn("estoque_maximo", Material.validar({**dados, "estoque_maximo": "3"})[1])

        data = date.today() - timedelta(days=1)

        def registrar(tipo, linhas):
            with self.app.app_context():
                form = MultiDict([("tipo", tipo), ("data", data.isoformat())])
                for item_id, quantidade in linhas:
                    form.add("item_id", str(item_id))
                    form.add("quantidade", quantidade)
                movimentacao, erros = Movimentacao.registrar(form)
                if movimentacao:
                    self.assertEqual(movimentacao.data, data)
                    self.assertEqual(movimentacao.criado_em.date(), date.today())
                return not erros

        def simultaneas(tipo, quantidade):
            barreira = Barrier(2, timeout=5)
            ler_linhas = Movimentacao._ler_linhas

            def aguardar(dados, erros):
                linhas = ler_linhas(dados, erros)
                barreira.wait()
                return linhas

            with patch.object(Movimentacao, "_ler_linhas", side_effect=aguardar):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futuros = [
                        pool.submit(registrar, tipo, [(ids[0], quantidade)]) for _ in range(2)
                    ]
                    return [futuro.result() for futuro in futuros]

        self.assertEqual(sorted(simultaneas("SAIDA", "7")), [False, True])
        self.assertFalse(registrar("SAIDA", [(ids[0], "1"), (ids[1], "3")]))
        with self.app.app_context():
            self.assertEqual(db.session.get(ItemEstoque, ids[0]).quantidade, 3)
            self.assertEqual(Movimentacao.query.count(), 3)
            self.assertTrue(db.session.get(ItemEstoque, ids[0]).abaixo_do_medio)

        self.assertTrue(all(simultaneas("ENTRADA", "1")))
        with self.app.app_context():
            item = db.session.get(ItemEstoque, ids[0])
            self.assertEqual(item.quantidade, Decimal("5.000"))
            self.assertFalse(item.abaixo_do_medio)
            self.assertEqual(Movimentacao.query.count(), 5)
