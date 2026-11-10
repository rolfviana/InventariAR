const root = document.querySelector("#app");
const config = window.INVENTARIAR_CONFIG || {};
const state = {
  token: sessionStorage.getItem("inventariar_token") || "",
  user: JSON.parse(sessionStorage.getItem("inventariar_user") || "null"),
  items: [],
  filter: ""
};

const icon = {
  grid: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  box: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 8 9 5 9-5M3 8v9l9 5 9-5V8M12 13v9"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  logout: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7"/></svg>'
};

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function currentRoute() {
  return (location.hash.replace(/^#/, "") || "/").split("?")[0];
}

function setRoute(route) {
  location.hash = route;
}

function showNotice(message, type = "error") {
  const notice = document.querySelector("#notice");
  if (!notice) return;
  notice.className = `notice ${type}`;
  notice.textContent = message;
  notice.hidden = !message;
}

function apiUrl(path) {
  const base = (config.apiBaseUrl || "").replace(/\/+$/, "");
  if (!base) throw new Error("Configure apiBaseUrl em frontend/config.js.");
  return `${base}${path}`;
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(apiUrl(path), {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
        ...options.headers
      }
    });
  } catch {
    throw new Error("Não foi possível conectar à API Flask. Confira se o backend está em execução.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      signOut();
      setRoute("/login");
    }
    const fields = data.error?.fields || {};
    const details = Object.entries(fields).map(([field, text]) => `${field}: ${text}`).join(" · ");
    throw new Error([data.error?.message || "A API recusou a operação.", details].filter(Boolean).join(" "));
  }
  return data;
}

function signOut() {
  state.token = "";
  state.user = null;
  sessionStorage.removeItem("inventariar_token");
  sessionStorage.removeItem("inventariar_user");
}

function renderLogin() {
  const signUp = new URLSearchParams(location.hash.split("?")[1] || "").get("cadastro") === "1";
  root.innerHTML = `
    <main class="login-page">
      <a class="brand brand-login" href="#/"><span class="brand-mark">I</span><span>Inventari<span class="brand-accent">AR</span></span></a>
      <section class="login-card">
        <p class="eyebrow">— ${signUp ? "Nova conta" : "Login"}</p>
        <h1>${signUp ? "Crie seu acesso." : "Bem-vindo de volta."}</h1>
        <p class="muted">${signUp ? "Crie uma conta para acessar o inventário." : "Entre para acessar o painel de inventário."}</p>
        <div id="notice" class="notice" hidden></div>
        <form id="login-form" class="stack">
          ${signUp ? '<label>Nome<input name="nome" required maxlength="120" autocomplete="name" placeholder="Seu nome"></label>' : ""}
          <label>E-mail<input name="email" type="email" required autocomplete="email" placeholder="voce@empresa.com"></label>
          <label>Senha<input name="password" type="password" required minlength="8" autocomplete="${signUp ? "new-password" : "current-password"}" placeholder="Mínimo de 8 caracteres"></label>
          <button class="button button-primary" type="submit">${signUp ? "Criar conta" : "Entrar"} ${icon.arrow}</button>
        </form>
        <p class="login-switch">${signUp ? "Já tem acesso?" : "Ainda não tem conta?"}
          <a href="#/login${signUp ? "" : "?cadastro=1"}">${signUp ? "Entrar" : "Criar conta"}</a>
        </p>
        <p class="small-note">Sua conta fica no banco local deste projeto.</p>
      </section>
    </main>`;

  document.querySelector("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const button = event.currentTarget.querySelector("button");
    button.disabled = true;
    showNotice("");
    try {
      const data = await api(signUp ? "/api/auth/register" : "/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
          ...(signUp ? { nome: form.get("nome") } : {})
        })
      });
      state.token = data.access_token;
      state.user = data.user;
      sessionStorage.setItem("inventariar_token", state.token);
      sessionStorage.setItem("inventariar_user", JSON.stringify(state.user));
      setRoute("/dashboard");
    } catch (error) {
      showNotice(error.message);
      button.disabled = false;
    }
  });
}

function appFrame(title, active, content) {
  const email = state.user?.email || "Conta conectada";
  root.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar">
        <a class="brand" href="#/dashboard"><span class="brand-mark">I</span><span>Inventari<span class="brand-accent">AR</span></span></a>
        <p class="nav-caption">PATRIMÔNIO</p>
        <nav class="side-nav">
          <a class="${active === "dashboard" ? "active" : ""}" href="#/dashboard">${icon.grid}<span>Visão geral</span></a>
          <a class="${active === "equipamentos" ? "active" : ""}" href="#/equipamentos">${icon.box}<span>Equipamentos</span></a>
          <a class="${active === "cadastrar" ? "active" : ""}" href="#/cadastrar">${icon.plus}<span>Novo cadastro</span></a>
        </nav>
        <div class="sidebar-bottom">
          <div class="account"><span class="avatar">${esc(email.slice(0, 1).toUpperCase())}</span><span class="account-email">${esc(email)}</span></div>
          <button class="button button-quiet" id="logout">${icon.logout}<span>Sair</span></button>
          <p class="sidebar-foot">InventariAR · Projeto acadêmico</p>
        </div>
      </aside>
      <main class="main-content">
        <header class="topbar"><span class="topbar-label">Inventário / ${esc(title)}</span><span class="live-pill"><i></i> Dados da API</span></header>
        <div class="content-wrap">
          <div id="notice" class="notice" hidden></div>
          ${content}
        </div>
      </main>
    </div>`;
  document.querySelector("#logout").addEventListener("click", () => {
    signOut();
    setRoute("/login");
  });
}

function statusPill(status) {
  return `<span class="pill ${status === "ativo" ? "pill-green" : "pill-gray"}">${status === "ativo" ? "Ativo" : "Inativo"}</span>`;
}

function conditionPill(condition) {
  const labels = { excelente: "Excelente", bom: "Bom", aceitavel: "Aceitável", regular: "Regular", ruim: "Ruim" };
  const className = condition === "ruim" ? "pill-red" : condition === "regular" || condition === "aceitavel" ? "pill-amber" : "pill-gray";
  return `<span class="pill ${className}">${esc(labels[condition] || condition)}</span>`;
}

function emptyState(message) {
  return `<div class="empty-state"><div class="empty-icon">${icon.box}</div><h3>Nenhum equipamento encontrado</h3><p>${esc(message)}</p><a class="button button-primary" href="#/cadastrar">${icon.plus} Cadastrar equipamento</a></div>`;
}

function equipmentTable(items, actions = true) {
  if (!items.length) return emptyState("Cadastre o primeiro equipamento ou ajuste os filtros.");
  return `<div class="table-wrap"><table>
    <thead><tr><th>Equipamento</th><th>Tombamento</th><th>Categoria</th><th>Localização</th><th>Condição</th><th>Status</th>${actions ? "<th>Ações</th>" : ""}</tr></thead>
    <tbody>${items.map((item) => `<tr>
      <td><strong>${esc(item.nome)}</strong></td>
      <td><code>${esc(item.tombamento)}</code></td>
      <td>${esc(item.categoria)}</td>
      <td>${esc(item.local)}</td>
      <td>${conditionPill(item.condicao)}</td>
      <td>${statusPill(item.status)}</td>
      ${actions ? `<td><div class="row-actions"><button class="text-button" data-action="edit" data-id="${esc(item.id)}">Editar</button><button class="text-button" data-action="move" data-id="${esc(item.id)}">Movimentar</button><button class="text-button danger-text" data-action="delete" data-id="${esc(item.id)}">Excluir</button></div></td>` : ""}
    </tr>`).join("")}</tbody>
  </table></div>`;
}

async function loadEquipment(query = "") {
  const suffix = query ? `?busca=${encodeURIComponent(query)}` : "";
  const data = await api(`/api/equipamentos${suffix}`);
  state.items = data.equipamentos || [];
  return state.items;
}

function dashboardContent(items) {
  const active = items.filter((item) => item.status === "ativo").length;
  const inactive = items.length - active;
  const attention = items.filter((item) => item.condicao === "ruim" || item.condicao === "regular").length;
  const categories = new Set(items.map((item) => item.categoria)).size;
  const latest = [...items].sort((a, b) => b.criadoEm.localeCompare(a.criadoEm)).slice(0, 5);
  return `
    <section class="page-heading">
      <div><p class="eyebrow">— Painel de controle</p><h1>Visão geral do patrimônio.</h1><p class="muted">Acompanhe os equipamentos cadastrados e suas condições atuais.</p></div>
      <a class="button button-primary" href="#/cadastrar">${icon.plus} Novo equipamento</a>
    </section>
    <section class="stats-grid">
      <article class="stat-card"><span class="stat-label">Equipamentos</span><strong>${items.length}</strong><span class="stat-caption">Registros no banco</span></article>
      <article class="stat-card"><span class="stat-label">Ativos</span><strong>${active}</strong><span class="stat-caption">${inactive} inativos</span></article>
      <article class="stat-card"><span class="stat-label">Precisam de atenção</span><strong>${attention}</strong><span class="stat-caption">Condição regular ou ruim</span></article>
      <article class="stat-card"><span class="stat-label">Categorias</span><strong>${categories}</strong><span class="stat-caption">Tipos cadastrados</span></article>
    </section>
    <section class="panel">
      <div class="panel-heading"><div><p class="eyebrow">— Atualizações recentes</p><h2>Últimos equipamentos</h2></div><a class="text-link" href="#/equipamentos">Ver todos ${icon.arrow}</a></div>
      ${equipmentTable(latest, false)}
    </section>
    <p class="data-caption">Os números acima são calculados a partir dos dados retornados pela API Flask.</p>`;
}

async function renderDashboard() {
  appFrame("Visão geral", "dashboard", '<div class="loading">Carregando dados persistidos...</div>');
  try {
    const items = await loadEquipment();
    document.querySelector(".content-wrap").innerHTML = dashboardContent(items);
  } catch (error) {
    showNotice(error.message);
    document.querySelector(".content-wrap").innerHTML += '<button class="button button-secondary" id="retry">Tentar novamente</button>';
    document.querySelector("#retry").addEventListener("click", renderDashboard);
  }
  bindTableActions();
}

function renderEquipmentPage(items = state.items, query = "") {
  appFrame("Equipamentos", "equipamentos", `
    <section class="page-heading">
      <div><p class="eyebrow">— Gestão de patrimônio</p><h1>Equipamentos.</h1><p class="muted">Pesquise por tombamento, nome, categoria ou localização.</p></div>
      <a class="button button-primary" href="#/cadastrar">${icon.plus} Novo equipamento</a>
    </section>
    <section class="panel">
      <form class="filter-form" id="search-form">
        <label class="search-field">${icon.search}<input name="busca" value="${esc(query)}" placeholder="Buscar equipamento..." aria-label="Buscar equipamento"></label>
        <button class="button button-secondary" type="submit">Buscar</button>
      </form>
      <div id="equipment-list">${equipmentTable(items)}</div>
    </section>`);
  document.querySelector("#search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get("busca").trim();
    try {
      renderEquipmentPage(await loadEquipment(value), value);
    } catch (error) {
      showNotice(error.message);
    }
  });
  bindTableActions();
}

async function renderEquipmentList() {
  appFrame("Equipamentos", "equipamentos", '<div class="loading">Carregando equipamentos...</div>');
  try {
    renderEquipmentPage(await loadEquipment());
  } catch (error) {
    showNotice(error.message);
    document.querySelector(".content-wrap").innerHTML += '<button class="button button-secondary" id="retry">Tentar novamente</button>';
    document.querySelector("#retry").addEventListener("click", renderEquipmentList);
  }
}

function equipmentForm(item = {}) {
  return `<form id="equipment-form" class="form-grid">
    <label>Nome do equipamento<input name="nome" required maxlength="200" value="${esc(item.nome || "")}" placeholder="Ex.: Notebook Dell"></label>
    <label>Número de tombamento<input name="tombamento" required maxlength="80" value="${esc(item.tombamento || "")}" placeholder="Ex.: IFRO-001"></label>
    <label>Categoria<input name="categoria" required maxlength="120" value="${esc(item.categoria || "")}" placeholder="Ex.: Informática"></label>
    <label>Localização<input name="local" required maxlength="160" value="${esc(item.local || "")}" placeholder="Ex.: Laboratório 02"></label>
    <label>Condição<select name="condicao" required>${optionList(["excelente", "bom", "aceitavel", "regular", "ruim"], item.condicao || "excelente")}</select></label>
    <label>Status<select name="status" required>${optionList(["ativo", "inativo"], item.status || "ativo")}</select></label>
    <div class="form-actions"><a class="button button-secondary" href="#/equipamentos">Cancelar</a><button class="button button-primary" type="submit">${item.id ? "Salvar alterações" : "Cadastrar equipamento"}</button></div>
  </form>`;
}

function optionList(values, selected) {
  const labels = { aceitavel: "Aceitável", ativo: "Ativo", inativo: "Inativo" };
  return values.map((value) => `<option value="${value}" ${value === selected ? "selected" : ""}>${labels[value] || value[0].toUpperCase() + value.slice(1)}</option>`).join("");
}

function renderCreatePage() {
  appFrame("Novo cadastro", "cadastrar", `
    <section class="page-heading"><div><p class="eyebrow">— Cadastro</p><h1>Novo equipamento.</h1><p class="muted">Preencha os dados principais do patrimônio.</p></div></section>
    <section class="panel form-panel"><div id="notice" class="notice" hidden></div>${equipmentForm()}</section>`);
  document.querySelector("#equipment-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      const fields = Object.fromEntries(new FormData(event.currentTarget));
      await api("/api/equipamentos", { method: "POST", body: JSON.stringify(fields) });
      setRoute("/equipamentos");
    } catch (error) {
      showNotice(error.message);
      button.disabled = false;
    }
  });
}

function bindTableActions() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const item = state.items.find((row) => row.id === button.dataset.id);
      if (!item) return;
      if (button.dataset.action === "delete") {
        if (!confirm(`Excluir ${item.nome} (${item.tombamento})? O histórico desse equipamento também será removido.`)) return;
        try {
          await api(`/api/equipamentos/${encodeURIComponent(item.id)}`, { method: "DELETE" });
          await renderEquipmentList();
        } catch (error) {
          showNotice(error.message);
        }
      } else if (button.dataset.action === "edit") {
        openEditor(item);
      } else if (button.dataset.action === "move") {
        openMovement(item);
      }
    });
  });
}

function openDialog(title, body) {
  const dialog = document.createElement("dialog");
  dialog.className = "modal";
  dialog.innerHTML = `<div class="modal-heading"><div><p class="eyebrow">— InventariAR</p><h2>${esc(title)}</h2></div><button class="close-button" aria-label="Fechar">×</button></div><div class="modal-body">${body}</div>`;
  document.body.append(dialog);
  dialog.querySelector(".close-button").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  dialog.showModal();
  return dialog;
}

function openEditor(item) {
  const dialog = openDialog("Editar equipamento", equipmentForm(item));
  dialog.querySelector("#equipment-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      const fields = Object.fromEntries(new FormData(event.currentTarget));
      await api(`/api/equipamentos/${encodeURIComponent(item.id)}`, { method: "PUT", body: JSON.stringify(fields) });
      dialog.close();
      await renderEquipmentList();
    } catch (error) {
      dialog.querySelector(".modal-body").insertAdjacentHTML("afterbegin", `<div class="notice">${esc(error.message)}</div>`);
      button.disabled = false;
    }
  });
}

function openMovement(item) {
  const dialog = openDialog("Movimentar equipamento", `
    <p class="muted">${esc(item.nome)} · ${esc(item.tombamento)}</p>
    <form id="movement-form" class="form-grid">
      <label>Novo local<input name="local" required maxlength="160" value="${esc(item.local)}"></label>
      <label>Condição<select name="condicao">${optionList(["excelente", "bom", "aceitavel", "regular", "ruim"], item.condicao)}</select></label>
      <label>Status<select name="status">${optionList(["ativo", "inativo"], item.status)}</select></label>
      <label class="full-field">Motivo<input name="motivo" required maxlength="500" placeholder="Descreva o motivo da movimentação"></label>
      <div class="form-actions"><button class="button button-secondary close-dialog" type="button">Cancelar</button><button class="button button-primary" type="submit">Registrar movimentação</button></div>
    </form>`);
  dialog.querySelector(".close-dialog").addEventListener("click", () => dialog.close());
  dialog.querySelector("#movement-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      await api(`/api/equipamentos/${encodeURIComponent(item.id)}/movimentacoes`, {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget)))
      });
      dialog.close();
      await renderEquipmentList();
    } catch (error) {
      dialog.querySelector(".modal-body").insertAdjacentHTML("afterbegin", `<div class="notice">${esc(error.message)}</div>`);
      button.disabled = false;
    }
  });
}

async function render() {
  const route = currentRoute();
  if (!state.token && route !== "/login" && route !== "/") {
    setRoute("/login");
    return;
  }
  if (route === "/login" || !state.token) {
    renderLogin();
    return;
  }
  if (route === "/cadastrar") {
    renderCreatePage();
    return;
  }
  if (route === "/equipamentos") {
    await renderEquipmentList();
    return;
  }
  await renderDashboard();
}

window.addEventListener("hashchange", render);
render();
