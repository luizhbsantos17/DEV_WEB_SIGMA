"""Adiciona limites de estoque, categoria dos produtos e usuários."""

import sqlalchemy as sa
from alembic import op

revision = "ba3a961ce640"
down_revision = "33df4ef26411"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("itens_estoque", sa.Column("estoque_medio", sa.Numeric(12, 3)))
    op.add_column("itens_estoque", sa.Column("estoque_maximo", sa.Numeric(12, 3)))

    with op.batch_alter_table("produtos") as batch:
        batch.add_column(sa.Column("categoria", sa.String(20), nullable=False, server_default="Geral"))
        batch.alter_column("genero", existing_type=sa.String(20), nullable=True)
        batch.create_check_constraint("ck_produto_categoria", "categoria IN ('Geral', 'Infantil')")

    op.execute("UPDATE produtos SET categoria = 'Infantil', genero = NULL WHERE genero = 'Infantil'")

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(40), nullable=False, unique=True),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(15), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("troca_obrigatoria", sa.Boolean(), nullable=False),
        sa.Column("versao_sessao", sa.String(32), nullable=False),
        sa.CheckConstraint("perfil IN ('admin', 'funcionario')", name="ck_usuario_perfil"),
    )


def downgrade():
    op.execute("UPDATE produtos SET genero = 'Infantil' WHERE categoria = 'Infantil' OR genero IS NULL")
    with op.batch_alter_table("produtos") as batch:
        batch.drop_constraint("ck_produto_categoria", type_="check")
        batch.drop_column("categoria")
        batch.alter_column("genero", existing_type=sa.String(20), nullable=False)

    # SQLite >= 3.35 permite remover estas colunas sem recriar a tabela
    # referenciada pelos produtos, materiais e itens movimentados.
    op.drop_column("itens_estoque", "estoque_maximo")
    op.drop_column("itens_estoque", "estoque_medio")
    op.drop_table("usuarios")
