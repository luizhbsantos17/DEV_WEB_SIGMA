// Modal de exclusão: preenche a ação do formulário e o nome do item clicado.
const modalExclusao = document.getElementById("modalExclusao");
if (modalExclusao) {
  modalExclusao.addEventListener("show.bs.modal", (evento) => {
    const botao = evento.relatedTarget;
    document.getElementById("formExclusao").action = botao.dataset.url;
    document.getElementById("nomeExclusao").textContent = botao.dataset.nome;
  });
}

// Nova movimentação: adicionar e remover linhas de itens.
const linhas = document.getElementById("linhas");
const modeloLinha = document.getElementById("modeloLinha");
const botaoAdicionar = document.getElementById("adicionarLinha");

if (linhas && modeloLinha && botaoAdicionar) {
  botaoAdicionar.addEventListener("click", () => {
    linhas.appendChild(modeloLinha.content.cloneNode(true));
  });

  linhas.addEventListener("click", (evento) => {
    const botao = evento.target.closest(".remover-linha");
    if (!botao) return;
    const linha = botao.closest(".linha-item");
    if (linhas.querySelectorAll(".linha-item").length > 1) {
      linha.remove();
    } else {
      linha.querySelectorAll("select, input").forEach((campo) => { campo.value = ""; });
    }
  });
}

// Nova movimentação: o botão acompanha o tipo escolhido (Entrada/Saída).
const botaoRegistrar = document.getElementById("botaoRegistrar");
const tipoSaida = document.getElementById("tipoSaida");

function atualizarBotaoRegistrar() {
  if (!botaoRegistrar || !tipoSaida) return;
  const saida = tipoSaida.checked;
  botaoRegistrar.textContent = saida ? "Registrar saída" : "Registrar entrada";
  botaoRegistrar.classList.toggle("btn-danger", saida);
  botaoRegistrar.classList.toggle("btn-success", !saida);
}

document.querySelectorAll('input[name="tipo"]').forEach((radio) => {
  radio.addEventListener("change", atualizarBotaoRegistrar);
});
atualizarBotaoRegistrar();