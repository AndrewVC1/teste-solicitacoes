const lista = document.querySelector("#lista");
const lado = document.querySelector("#lado");
const botaoNova = document.querySelector("#nova");

function esc(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function lerJson(resposta) {
  const corpo = await resposta.json();
  if (!resposta.ok) {
    const detalhe = corpo.detail ?? "Não foi possível concluir.";
    throw new Error(typeof detalhe === "string" ? detalhe : "Dados inválidos.");
  }
  return corpo;
}

function desenharLista(solicitacoes, codigoAberto) {
  if (solicitacoes.length === 0) {
    lista.innerHTML = '<li class="vazio">Nenhuma solicitação ainda.</li>';
    return;
  }
  lista.innerHTML = solicitacoes.map((item) => {
    const titulo = esc(item.dados.titulo || item.codigo);
    const ativa = item.codigo === codigoAberto ? " ativa" : "";
    return `<li><button type="button" class="${ativa}" data-codigo="${esc(item.codigo)}">${titulo}<br>${esc(item.codigo)}</button></li>`;
  }).join("");
}

function abrirPainel(item) {
  const campos = Object.entries(item.dados).map(([nome, valor]) => {
    return `<p><strong>${esc(nome)}</strong><br>${esc(valor)}</p>`;
  }).join("");
  lado.innerHTML = `
    <article class="painel">
      <h2>${esc(item.codigo)}</h2>
      <p>${esc(item.status)} · ${esc(item.criado_em)}</p>
      ${campos}
    </article>`;
}

async function carregar(codigoAberto) {
  const solicitacoes = await lerJson(await fetch("/solicitacoes"));
  desenharLista(solicitacoes, codigoAberto);
  return solicitacoes;
}

async function montarFormulario() {
  const campos = await lerJson(await fetch("/schema-campos"));
  const html = campos.map((campo) => {
    const obrigatorio = campo.obrigatorio ? "required" : "";
    const nome = esc(campo.nome);
    const rotulo = esc(campo.rotulo);
    if (campo.tipo === "selecao") {
      const opcoes = (campo.opcoes || []).map((opcao) => {
        return `<option value="${esc(opcao)}">${esc(opcao)}</option>`;
      }).join("");
      return `<label><span>${rotulo}</span><select name="${nome}" ${obrigatorio}><option value="">Selecione</option>${opcoes}</select></label>`;
    }
    if (campo.tipo === "texto_longo") {
      return `<label><span>${rotulo}</span><textarea name="${nome}" ${obrigatorio}></textarea></label>`;
    }
    return `<label><span>${rotulo}</span><input name="${nome}" ${obrigatorio}></label>`;
  }).join("");
  lado.innerHTML = `<form>${html}<p class="erro" id="erro"></p><button class="enviar" type="submit">Abrir solicitação</button></form>`;
}

lista.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("button[data-codigo]");
  if (!botao) return;
  const codigo = botao.dataset.codigo;
  const item = await lerJson(await fetch("/solicitacoes/" + encodeURIComponent(codigo)));
  await carregar(item.codigo);
  abrirPainel(item);
});

botaoNova.addEventListener("click", () => {
  montarFormulario().catch((erro) => {
    lado.innerHTML = `<p class="erro">${esc(erro.message)}</p>`;
  });
});

lado.addEventListener("submit", async (evento) => {
  const form = evento.target;
  if (form.tagName !== "FORM") return;
  evento.preventDefault();
  const dados = Object.fromEntries(new FormData(form));
  const erro = document.querySelector("#erro");
  erro.textContent = "";
  try {
    const criada = await lerJson(await fetch("/solicitacoes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dados }),
    }));
    await carregar(criada.codigo);
    abrirPainel(criada);
  } catch (falha) {
    erro.textContent = falha.message;
  }
});

carregar().catch((erro) => {
  lista.innerHTML = `<li class="erro">${esc(erro.message)}</li>`;
});
