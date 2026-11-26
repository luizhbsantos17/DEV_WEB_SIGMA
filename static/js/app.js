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

function definirItemNaLinha(linha, opcao) {
  linha.querySelector('input[name="item_id"]').value = opcao?.dataset.itemId ?? "";
  const botao = linha.querySelector(".selecionar-item");
  botao.dataset.tipoItem = opcao?.dataset.tipoItem ?? "";
  botao.querySelector(".nome-item").textContent =
    opcao?.querySelector(".nome-item").textContent ?? "Selecionar item";
  botao.querySelector(".saldo-item").textContent =
    opcao?.querySelector(".saldo-item").textContent ?? "";
}

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
      definirItemNaLinha(linha, null);
      linha.querySelector('input[name="quantidade"]').value = "";
    }
  });
}

const seletorItens = document.getElementById("seletorItens");
if (seletorItens) {
  const busca = seletorItens.querySelector("#buscaSeletorItens");
  const abas = [...seletorItens.querySelectorAll('[role="tab"]')];
  const abaInicial = seletorItens.querySelector("#painel-material .opcao-item") ? abas[0] : abas[1];
  let linhaAtiva = null;

  function normalizar(texto) {
    return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("pt-BR");
  }

  const paineis = [...seletorItens.querySelectorAll('[role="tabpanel"]')].map((painel) => ({
    vazio: painel.querySelector(".sem-resultados"),
    opcoes: [...painel.querySelectorAll(".opcao-item")].map((opcao) => ({
      elemento: opcao,
      nome: normalizar(opcao.querySelector(".nome-item").textContent),
    })),
  }));

  function filtrarItens() {
    const termos = normalizar(busca.value).trim().split(/\s+/);
    for (const {vazio, opcoes} of paineis) {
      let encontrou = false;
      for (const {elemento, nome} of opcoes) {
        const corresponde = termos.every((termo) => nome.includes(termo));
        elemento.hidden = !corresponde;
        encontrou ||= corresponde;
      }
      vazio.hidden = encontrou;
    }
  }

  busca.addEventListener("input", filtrarItens);
  seletorItens.addEventListener("show.bs.modal", (evento) => {
    const botao = evento.relatedTarget;
    linhaAtiva = botao?.closest(".linha-item");
    const aba = abas.find((aba) => aba.dataset.tipoItem === botao?.dataset.tipoItem);
    bootstrap.Tab.getOrCreateInstance(aba ?? abaInicial).show();
    busca.value = "";
    filtrarItens();
  });
  seletorItens.addEventListener("shown.bs.modal", () => busca.focus());
  seletorItens.addEventListener("hidden.bs.modal", () => { linhaAtiva = null; });
  seletorItens.addEventListener("click", (evento) => {
    const opcao = evento.target.closest("[data-item-id]");
    if (!opcao || !linhaAtiva) return;
    definirItemNaLinha(linhaAtiva, opcao);
    bootstrap.Modal.getInstance(seletorItens).hide();
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
