/* LocalAI — chat interfeysi */
(() => {
  "use strict";

  const MD = window.LocalMarkdown;
  const STORE_KEY = "localai.v2";
  const $ = (id) => document.getElementById(id);

  const ICONS = {
    sidebar: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9.5 4v16"/>',
    compose: '<path d="M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/><path d="M18.4 2.6a2 2 0 0 1 3 3L12 15l-4 1 1-4Z"/>',
    paperclip: '<path d="m21.4 11.1-9.2 9.2a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5"/>',
    copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-2.64-6.36L21 8"/><path d="M21 3v5h-5"/>',
    folder: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    table: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    pencil: '<path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
    calculator: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01M8 18.5h8"/>',
    code: '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
    spell: '<path d="m4 16 5-12 5 12M5.7 12h6.6"/><path d="m15 19 2 2 4-4"/>',
    globe: '<circle cx="12" cy="12" r="9.5"/><path d="M2.5 12h19M12 2.5a14.5 14.5 0 0 1 0 19M12 2.5a14.5 14.5 0 0 0 0 19"/>',
    list: '<path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
    bulb: '<path d="M9 18h6M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2Z"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    chevron: '<path d="m9 18 6-6-6-6"/>',
    down: '<path d="M12 5v14M19 12l-7 7-7-7"/>',
    trash: '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9Z"/>',
  };
  const icon = (name, cls = "") => `<svg viewBox="0 0 24 24" class="${cls}" aria-hidden="true">${ICONS[name] || ICONS.file}</svg>`;
  const esc = MD.escape;

  const SUGGESTIONS = [
    { icon: "folder", title: "Papkani tahlil qil", sub: "Kompyuterdagi fayllarni ko'rib chiqadi", text: "Ish stolim (Desktop) papkasida nimalar borligini ko'rib, qisqacha tahlil qilib ber" },
    { icon: "code", title: "Kod yozib ber", sub: "Har qanday tilda, to'liq va ishlaydigan", text: "Python'da papkadagi fayllarni kengaytmasi bo'yicha alohida papkalarga ajratadigan skript yozib ber" },
    { icon: "table", title: "Jadvalni tahlil qil", sub: "Excel, CSV yoki JSON faylni biriktiring", text: "Biriktirgan jadvalimni tahlil qilib, eng muhim raqam va xulosalarni ayt", attach: true },
    { icon: "spell", title: "Imloni tuzat", sub: "Matndagi xatolarni topib tuzatadi", text: "/imlo " },
  ];

  const state = {
    chats: [],
    currentId: null,
    busy: false,
    controller: null,
    pending: [],
    think: false,
    status: null,
    skills: [],
    slash: { open: false, items: [], index: 0 },
    stick: true,
    maxUpload: 25 * 1024 * 1024,
  };

  const el = {
    thread: $("thread"), inner: $("threadInner"), input: $("input"), composer: $("composer"),
    send: $("sendBtn"), attach: $("attachBtn"), fileInput: $("fileInput"), pending: $("pendingFiles"),
    think: $("thinkBtn"), slash: $("slashMenu"), banner: $("banner"), sidebar: $("sidebar"), scrim: $("scrim"),
    chatList: $("chatList"), statusDot: $("statusDot"), popover: $("statusPopover"), scrollDown: $("scrollDown"),
    drop: $("dropOverlay"), toasts: $("toasts"),
  };

  /* -------------------------------------------------------------- utils */

  const uid = () => (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));
  const sizeText = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };
  const html = (strings, ...values) => strings.reduce((out, part, index) => out + part + (index < values.length ? values[index] : ""), "");
  const node = (markup) => {
    const template = document.createElement("template");
    template.innerHTML = markup.trim();
    return template.content.firstElementChild;
  };

  function toast(message, ms = 2200) {
    const item = node(`<div class="toast">${esc(message)}</div>`);
    el.toasts.appendChild(item);
    setTimeout(() => { item.classList.add("out"); setTimeout(() => item.remove(), 260); }, ms);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
  }

  /* ------------------------------------------------------------ storage */

  function load() {
    try {
      const data = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
      if (data && Array.isArray(data.chats)) {
        state.chats = data.chats;
        state.currentId = data.currentId;
        state.think = Boolean(data.think);
      }
    } catch { /* bo'sh holatdan boshlaymiz */ }
    for (const chat of state.chats) {
      for (const item of chat.items || []) {
        for (const block of item.blocks || []) {
          if (block.t === "tool" && block.status === "running") block.status = "stopped";
        }
      }
    }
  }

  function save() {
    const data = () => JSON.stringify({
      chats: state.chats.filter((chat) => chat.items.length),
      currentId: state.currentId,
      think: state.think,
    });
    for (let attempt = 0; attempt < 30; attempt++) {
      try {
        localStorage.setItem(STORE_KEY, data());
        return;
      } catch {
        const others = state.chats.filter((chat) => chat.id !== state.currentId && chat.items.length);
        if (!others.length) return;
        const oldest = others.reduce((a, b) => (a.updated < b.updated ? a : b));
        state.chats = state.chats.filter((chat) => chat !== oldest);
      }
    }
  }

  const blankChat = () => ({ id: uid(), title: "", created: Date.now(), updated: Date.now(), history: [], items: [] });

  function currentChat() {
    let chat = state.chats.find((item) => item.id === state.currentId);
    if (!chat) {
      chat = state.chats.find((item) => !item.items.length) || blankChat();
      if (!state.chats.includes(chat)) state.chats.unshift(chat);
      state.currentId = chat.id;
    }
    return chat;
  }

  /* ------------------------------------------------------------ scroll */

  const nearBottom = () => el.thread.scrollHeight - el.thread.scrollTop - el.thread.clientHeight < 90;
  function scrollToBottom(smooth = false) {
    el.thread.scrollTo({ top: el.thread.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  }
  el.thread.addEventListener("scroll", () => {
    state.stick = nearBottom();
    el.scrollDown.classList.toggle("show", !state.stick && el.thread.scrollHeight > el.thread.clientHeight + 200);
  }, { passive: true });
  el.scrollDown.innerHTML = icon("down");
  el.scrollDown.addEventListener("click", () => { state.stick = true; scrollToBottom(true); });

  /* ----------------------------------------------------------- welcome */

  function greeting() {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 11) return "Xayrli tong";
    if (hour >= 11 && hour < 17) return "Xayrli kun";
    if (hour >= 17 && hour < 23) return "Xayrli kech";
    return "Salom";
  }

  function renderWelcome() {
    const privateNote = state.status && state.status.private === false
      ? "Shaxsiy yordamchingiz — sozlangan Ollama serverida ishlaydi."
      : "Shaxsiy yordamchingiz — hammasi shu kompyuterda ishlaydi.";
    const view = node(html`
      <div class="welcome">
        <div class="orb hero"><span class="glow"></span></div>
        <h1>${greeting()}! Bugun nima qilamiz?</h1>
        <p>${privateNote}</p>
        <div class="suggestions"></div>
      </div>`);
    const grid = view.querySelector(".suggestions");
    SUGGESTIONS.forEach((item, index) => {
      const card = node(html`
        <button class="suggestion" type="button" style="animation-delay:${0.26 + index * 0.07}s">
          <span class="s-icon">${icon(item.icon)}</span>
          <span class="s-text"><strong>${esc(item.title)}</strong><span class="s-sub">${esc(item.sub)}</span></span>
        </button>`);
      card.addEventListener("click", () => {
        setInput(item.text);
        if (item.attach) el.fileInput.click();
      });
      grid.appendChild(card);
    });
    el.inner.appendChild(view);
  }

  /* ---------------------------------------------------------- rendering */

  function renderThread() {
    const chat = currentChat();
    el.inner.innerHTML = "";
    if (!chat.items.length) {
      renderWelcome();
    } else {
      chat.items.forEach((item) => {
        el.inner.appendChild(item.role === "user" ? userView(item) : assistantView(item, chat).root);
      });
      markLast();
    }
    requestAnimationFrame(() => { scrollToBottom(); state.stick = true; });
    renderChatList();
  }

  function fileChip(file, removable) {
    const chip = node(html`
      <span class="file-chip${file.status === "uploading" ? " uploading" : ""}">
        ${file.status === "uploading" ? '<span class="spinner"></span>' : icon(fileIcon(file.name))}
        <span class="name">${esc(file.name)}</span>
        <span class="size">${sizeText(file.size || 0)}</span>
      </span>`);
    if (removable) {
      const button = node(`<button type="button" aria-label="Olib tashlash">${icon("x")}</button>`);
      button.addEventListener("click", () => removePending(file.localId));
      chip.appendChild(button);
    }
    return chip;
  }

  function fileIcon(name) {
    const lower = String(name).toLowerCase();
    if (/\.(xlsx?|xlsm|csv|tsv|json)$/.test(lower)) return "table";
    if (/\.(py|js|ts|tsx|jsx|java|go|rs|c|cpp|cs|php|rb|kt|swift|sh|html|css|sql)$/.test(lower)) return "code";
    return "file";
  }

  function userView(item) {
    const root = node(`<div class="msg user"><div class="stack"></div></div>`);
    const stack = root.firstElementChild;
    if (item.files && item.files.length) {
      const chips = node(`<div class="file-chips"></div>`);
      item.files.forEach((file) => chips.appendChild(fileChip(file, false)));
      stack.appendChild(chips);
    }
    if (item.text) {
      const bubble = node(`<div class="bubble"></div>`);
      bubble.textContent = item.text;
      stack.appendChild(bubble);
    }
    return root;
  }

  function assistantView(item, chat) {
    const root = node(html`
      <div class="msg assistant">
        <span class="orb"></span>
        <div class="content"><div class="skill-chips"></div><div class="blocks"></div></div>
      </div>`);
    const view = {
      item,
      root,
      orb: root.querySelector(".orb"),
      content: root.querySelector(".content"),
      chips: root.querySelector(".skill-chips"),
      blocks: root.querySelector(".blocks"),
      liveText: null,
      liveBlock: null,
      thinkEl: null,
      thinkBlock: null,
      toolEls: new Map(),
      approvals: new Map(),
    };
    renderSkills(view);
    if (!item.skills || !item.skills.length) view.chips.remove();
    for (const block of item.blocks) view.blocks.appendChild(blockView(block, view));
    if (item.error) showError(view, item.error, chat);
    if (item.stopped) view.content.appendChild(node(`<div class="stopped-note">To'xtatildi</div>`));
    if (!item.streaming) addActions(view, chat);
    return view;
  }

  function renderSkills(view) {
    const skills = view.item.skills || [];
    view.chips.innerHTML = skills.map((skill) => `<span class="skill-chip">${icon(skill.icon)}${esc(skill.name)}</span>`).join("");
  }

  function blockView(block, view) {
    if (block.t === "text") {
      const div = node(`<div class="md"></div>`);
      div.innerHTML = MD.render(block.v);
      return div;
    }
    if (block.t === "think") return thinkingView(block, false);
    if (block.t === "tool") {
      const toolEl = toolView(block);
      view.toolEls.set(block.id, toolEl);
      return toolEl;
    }
    return document.createComment("");
  }

  function thinkingView(block, live) {
    const seconds = block.ms ? Math.max(1, Math.round(block.ms / 1000)) : 0;
    const label = live ? `<span class="shimmer">O'ylanmoqda…</span>` : `O'yladi${seconds ? ` · ${seconds} s` : ""}`;
    const details = node(html`
      <details class="thinking"${live ? " open" : ""}>
        <summary>${icon("sparkle")}<span class="t-label">${label}</span>${icon("chevron", "chev")}</summary>
        <div class="think-body"></div>
      </details>`);
    details.querySelector(".think-body").textContent = block.v;
    return details;
  }

  function toolView(block) {
    const root = node(html`
      <div class="tool">
        <button class="tool-head" type="button">
          <span class="t-icon">${icon(block.icon)}</span>
          <span class="t-text"><span class="t-action"></span><span class="t-target"></span></span>
          <span class="t-summary"></span>
          <span class="t-state"></span>
          ${icon("chevron", "chev")}
        </button>
        <div class="tool-body"><div><pre></pre></div></div>
      </div>`);
    root.querySelector(".tool-head").addEventListener("click", () => {
      if (root.querySelector("pre").textContent) root.classList.toggle("open");
    });
    updateToolView(root, block);
    return root;
  }

  function updateToolView(root, block) {
    root.querySelector(".t-action").textContent = block.action || block.name;
    root.querySelector(".t-target").textContent = block.target || "";
    root.querySelector(".t-target").title = block.target || "";
    const summary = root.querySelector(".t-summary");
    const stateEl = root.querySelector(".t-state");
    const pre = root.querySelector("pre");
    root.classList.remove("error", "denied");
    const states = {
      running: ['<span class="spinner"></span>', block.waiting ? "ruxsat kutilmoqda" : ""],
      done: [icon("check", "check"), block.summary || ""],
      error: [icon("x", "cross"), block.summary || "Xato"],
      denied: [icon("x", "cross"), "Rad etildi"],
      stopped: [icon("x", "cross"), "To'xtatildi"],
    };
    const [stateHtml, text] = states[block.status] || states.running;
    if (stateEl.dataset.status !== block.status) {
      stateEl.innerHTML = stateHtml;
      stateEl.dataset.status = block.status;
    }
    summary.textContent = text;
    if (block.status === "error") root.classList.add("error");
    if (block.status === "denied" || block.status === "stopped") root.classList.add("denied");
    pre.textContent = block.preview || "";
    root.querySelector(".chev").style.visibility = block.preview ? "visible" : "hidden";
    root.querySelector(".tool-head").disabled = !block.preview;
  }

  function showError(view, message, chat) {
    const notice = node(html`<div class="notice">${icon("alert")}<div>${MD.inline(message)}</div></div>`);
    if (chat) {
      const retry = node(`<button class="btn" type="button">${icon("refresh")}Qayta</button>`);
      retry.addEventListener("click", () => regenerate(view.item));
      notice.appendChild(retry);
    }
    view.content.appendChild(notice);
  }

  function addActions(view, chat) {
    const actions = node(`<div class="msg-actions"></div>`);
    const text = view.item.blocks.filter((block) => block.t === "text").map((block) => block.v).join("\n\n").trim();
    if (text) {
      const copy = node(`<button class="icon-btn" type="button" aria-label="Nusxa olish" title="Nusxa olish">${icon("copy")}</button>`);
      copy.addEventListener("click", async () => {
        await copyText(text);
        copy.innerHTML = icon("check");
        setTimeout(() => { copy.innerHTML = icon("copy"); }, 1400);
      });
      actions.appendChild(copy);
    }
    const retry = node(`<button class="icon-btn" type="button" aria-label="Qayta javob" title="Qayta javob">${icon("refresh")}</button>`);
    retry.addEventListener("click", () => regenerate(view.item));
    actions.appendChild(retry);
    view.content.appendChild(actions);
  }

  function markLast() {
    const messages = el.inner.querySelectorAll(".msg.assistant");
    messages.forEach((message, index) => message.classList.toggle("last", index === messages.length - 1));
  }

  /* -------------------------------------------------------- sidebar list */

  function renderChatList() {
    const chats = state.chats.filter((chat) => chat.items.length).sort((a, b) => b.updated - a.updated);
    el.chatList.innerHTML = "";
    if (!chats.length) {
      el.chatList.appendChild(node(`<li class="chat-empty">Hozircha suhbatlar yo'q</li>`));
      return;
    }
    const startOfDay = new Date().setHours(0, 0, 0, 0);
    const groups = [
      ["Bugun", (time) => time >= startOfDay],
      ["Kecha", (time) => time >= startOfDay - 864e5],
      ["Oxirgi 7 kun", (time) => time >= startOfDay - 7 * 864e5],
      ["Avvalroq", () => true],
    ];
    let lastGroup = null;
    for (const chat of chats) {
      const group = groups.find(([, test]) => test(chat.updated))[0];
      if (group !== lastGroup) {
        el.chatList.appendChild(node(`<li class="chat-group">${group}</li>`));
        lastGroup = group;
      }
      const item = node(html`
        <li class="chat-item${chat.id === state.currentId ? " active" : ""}">
          <button class="open" type="button"></button>
          <button class="icon-btn" type="button" aria-label="O'chirish" title="O'chirish">${icon("trash")}</button>
        </li>`);
      const open = item.querySelector(".open");
      open.textContent = chat.title || "Yangi suhbat";
      open.title = chat.title || "";
      open.addEventListener("click", () => {
        if (state.busy) return toast("Avval joriy javob tugashini kuting");
        state.currentId = chat.id;
        save();
        renderThread();
        closeSidebar();
      });
      item.querySelector(".icon-btn").addEventListener("click", () => deleteChat(chat.id));
      el.chatList.appendChild(item);
    }
  }

  function deleteChat(id) {
    if (state.busy && id === state.currentId) return toast("Avval joriy javob tugashini kuting");
    state.chats = state.chats.filter((chat) => chat.id !== id);
    fetch("/api/forget", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: id }) }).catch(() => {});
    if (state.currentId === id) state.currentId = null;
    save();
    renderThread();
    toast("Suhbat o'chirildi");
  }

  function openSidebar() { el.sidebar.classList.add("open"); el.scrim.classList.add("show"); renderChatList(); }
  function closeSidebar() { el.sidebar.classList.remove("open"); el.scrim.classList.remove("show"); }

  function newChat() {
    if (state.busy) return toast("Avval joriy javob tugashini kuting");
    const chat = currentChat();
    if (chat.items.length) {
      const fresh = blankChat();
      state.chats.unshift(fresh);
      state.currentId = fresh.id;
    }
    save();
    renderThread();
    closeSidebar();
    el.input.focus();
  }

  /* ------------------------------------------------------------ composer */

  function setInput(text) {
    el.input.value = text;
    autosize();
    el.input.focus();
    el.input.setSelectionRange(text.length, text.length);
    updateSend();
    updateSlash();
  }

  function autosize() {
    el.input.style.height = "auto";
    el.input.style.height = `${Math.min(el.input.scrollHeight, window.innerHeight * 0.4)}px`;
  }

  function updateSend() {
    const uploading = state.pending.some((file) => file.status === "uploading");
    const hasContent = el.input.value.trim() || state.pending.some((file) => file.status === "ready");
    el.send.classList.toggle("stop", state.busy);
    el.send.disabled = state.busy ? false : !hasContent || uploading;
    el.send.setAttribute("aria-label", state.busy ? "To'xtatish" : "Yuborish");
  }

  function renderPending() {
    el.pending.innerHTML = "";
    state.pending.forEach((file) => el.pending.appendChild(fileChip(file, true)));
    updateSend();
  }

  function removePending(localId) {
    const file = state.pending.find((item) => item.localId === localId);
    state.pending = state.pending.filter((item) => item.localId !== localId);
    if (file && file.id) fetch(`/api/upload/${encodeURIComponent(file.id)}`, { method: "DELETE" }).catch(() => {});
    renderPending();
  }

  async function addFiles(list) {
    for (const file of Array.from(list || [])) {
      if (state.pending.length >= 10) { toast("Bir xabarga ko'pi bilan 10 ta fayl"); break; }
      if (file.size > state.maxUpload) { toast(`${file.name}: ${sizeText(state.maxUpload)} dan katta`); continue; }
      if (!file.size) { toast(`${file.name}: fayl bo'sh`); continue; }
      const entry = { localId: uid(), name: file.name, size: file.size, status: "uploading" };
      state.pending.push(entry);
      renderPending();
      try {
        const response = await fetch(`/api/upload?name=${encodeURIComponent(file.name)}`, {
          method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.ok) throw new Error(data.error || "Faylni yuklab bo'lmadi");
        Object.assign(entry, { id: data.id, name: data.name, status: "ready" });
      } catch (error) {
        state.pending = state.pending.filter((item) => item !== entry);
        toast(error.message || "Faylni yuklab bo'lmadi");
      }
      renderPending();
    }
    el.input.focus();
  }

  /* ---------------------------------------------------------- slash menu */

  function updateSlash() {
    const value = el.input.value;
    const match = value.match(/^\/(\S*)$/);
    if (!match || !state.skills.length) return closeSlash();
    const query = match[1].toLowerCase();
    const rank = (skill) => {
      if (!query || skill.command.slice(1).startsWith(query) || skill.name.toLowerCase().startsWith(query)) return 0;
      return query.length >= 3 && skill.description.toLowerCase().includes(query) ? 1 : -1;
    };
    const items = state.skills.filter((skill) => rank(skill) >= 0).sort((a, b) => rank(a) - rank(b));
    if (!items.length) return closeSlash();
    state.slash = { open: true, items, index: Math.min(state.slash.index, items.length - 1) };
    el.slash.innerHTML = "";
    items.forEach((skill, index) => {
      const button = node(html`
        <button class="slash-item${index === state.slash.index ? " active" : ""}" type="button" role="option">
          <span class="s-icon">${icon(skill.icon)}</span>
          <span class="label"><span><span class="name">${esc(skill.name)}</span><span class="cmd">${esc(skill.command)}</span></span>
          <span class="desc">${esc(skill.description)}</span></span>
        </button>`);
      button.addEventListener("mousedown", (event) => { event.preventDefault(); chooseSlash(index); });
      el.slash.appendChild(button);
    });
    el.slash.hidden = false;
  }

  function moveSlash(step) {
    const { items } = state.slash;
    state.slash.index = (state.slash.index + step + items.length) % items.length;
    [...el.slash.children].forEach((child, index) => child.classList.toggle("active", index === state.slash.index));
    el.slash.children[state.slash.index].scrollIntoView({ block: "nearest" });
  }

  function chooseSlash(index) {
    const skill = state.slash.items[index];
    closeSlash();
    if (skill) setInput(`${skill.command} `);
  }

  function closeSlash() {
    state.slash.open = false;
    state.slash.index = 0;
    el.slash.hidden = true;
  }

  /* --------------------------------------------------------------- send */

  function chatTitle(text, files) {
    let line = (text || "").split("\n")[0].trim();
    const command = line.match(/^\/(\S+)\s*/);
    if (command && state.skills.some((skill) => skill.command === `/${command[1]}`)) line = line.slice(command[0].length);
    const base = line || (files[0] && files[0].name) || "Yangi suhbat";
    return base.length > 60 ? `${base.slice(0, 57)}…` : base;
  }

  function submit() {
    if (state.busy) { stop(); return; }
    const text = el.input.value.trim();
    const files = state.pending.filter((file) => file.status === "ready");
    if (!text && !files.length) return;
    if (state.pending.some((file) => file.status === "uploading")) return toast("Fayllar yuklanmoqda…");
    el.input.value = "";
    state.pending = [];
    renderPending();
    autosize();
    closeSlash();
    send(text, files.map((file) => ({ id: file.id, name: file.name, size: file.size })));
  }

  function stop() {
    if (state.controller) state.controller.abort();
  }

  async function send(text, files, historyIndex) {
    const chat = currentChat();
    if (typeof historyIndex === "number") chat.history = chat.history.slice(0, historyIndex);
    if (!chat.items.length) el.inner.innerHTML = "";
    if (!chat.title) chat.title = chatTitle(text, files);

    const userItem = { role: "user", text, files, historyIndex: chat.history.length };
    const item = { role: "assistant", blocks: [], skills: [], streaming: true };
    chat.items.push(userItem, item);
    chat.updated = Date.now();

    el.inner.appendChild(userView(userItem));
    const view = assistantView(item, chat);
    view.content.classList.add("streaming");
    view.orb.classList.add("is-busy");
    const typing = node(`<div class="typing"><i></i><i></i><i></i></div>`);
    view.blocks.appendChild(typing);
    el.inner.appendChild(view.root);
    markLast();
    state.stick = true;
    requestAnimationFrame(() => scrollToBottom(true));

    state.busy = true;
    state.controller = new AbortController();
    updateSend();
    save();

    const received = [];
    let partial = "";
    let renderQueued = false;

    const flush = () => {
      renderQueued = false;
      if (view.liveText && view.liveBlock) view.liveText.innerHTML = MD.render(view.liveBlock.v);
      if (state.stick) scrollToBottom();
    };
    const queueRender = () => {
      if (!renderQueued) { renderQueued = true; requestAnimationFrame(flush); }
    };
    const clearTyping = () => typing.remove();
    const endThinking = () => {
      if (!view.thinkEl) return;
      view.thinkBlock.ms = Date.now() - view.thinkBlock.start;
      const seconds = Math.max(1, Math.round(view.thinkBlock.ms / 1000));
      view.thinkEl.querySelector(".t-label").textContent = `O'yladi · ${seconds} s`;
      view.thinkEl.open = false;
      view.thinkEl = null;
      view.thinkBlock = null;
    };
    const endText = () => {
      if (view.liveText) {
        flush();
        view.liveText.classList.remove("live");
      }
      view.liveText = null;
      view.liveBlock = null;
    };

    const handlers = {
      meta(event) {
        item.skills = event.skills || [];
        if (item.skills.length) {
          view.content.insertBefore(view.chips, view.blocks);
          renderSkills(view);
        }
      },
      message(event) {
        received.push(event.message);
        if (event.message.role === "assistant") partial = "";
      },
      thinking(event) {
        clearTyping();
        endText();
        if (!view.thinkEl) {
          view.thinkBlock = { t: "think", v: "", start: Date.now() };
          item.blocks.push(view.thinkBlock);
          view.thinkEl = thinkingView(view.thinkBlock, true);
          view.blocks.appendChild(view.thinkEl);
        }
        view.thinkBlock.v += event.delta;
        const body = view.thinkEl.querySelector(".think-body");
        body.textContent = view.thinkBlock.v;
        body.scrollTop = body.scrollHeight;
        if (state.stick) queueRender();
      },
      token(event) {
        clearTyping();
        endThinking();
        if (!view.liveText) {
          view.liveBlock = { t: "text", v: "" };
          item.blocks.push(view.liveBlock);
          view.liveText = node(`<div class="md live"></div>`);
          view.blocks.appendChild(view.liveText);
        }
        view.liveBlock.v += event.delta;
        partial += event.delta;
        queueRender();
      },
      tool(event) {
        clearTyping();
        endThinking();
        endText();
        const block = { t: "tool", id: event.id, name: event.name, icon: event.icon, action: event.action, target: event.target, status: "running" };
        item.blocks.push(block);
        const toolEl = toolView(block);
        view.toolEls.set(block.id, toolEl);
        view.blocks.appendChild(toolEl);
        queueRender();
      },
      approval(event) {
        const block = item.blocks.find((entry) => entry.t === "tool" && entry.id === event.tool_id);
        const toolEl = view.toolEls.get(event.tool_id);
        if (block && toolEl) { block.waiting = true; updateToolView(toolEl, block); }
        const card = approvalCard(event);
        view.approvals.set(event.id, card);
        (toolEl ? toolEl.after(card) : view.blocks.appendChild(card));
        state.stick = true;
        queueRender();
      },
      approval_done(event) {
        const card = view.approvals.get(event.id);
        if (card) { card.remove(); view.approvals.delete(event.id); }
      },
      tool_done(event) {
        const block = item.blocks.find((entry) => entry.t === "tool" && entry.id === event.id);
        if (!block) return;
        Object.assign(block, { status: event.status, summary: event.summary || "", preview: event.preview || "", waiting: false });
        const toolEl = view.toolEls.get(event.id);
        if (toolEl) updateToolView(toolEl, block);
        queueRender();
      },
      error(event) {
        item.error = event.message;
      },
      done() {},
      ping() {},
    };

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chat.id,
          message: text,
          history: chat.history.slice(-400),
          attachments: files.map((file) => file.id),
          think: state.think && !el.think.hidden,
        }),
        signal: state.controller.signal,
      });
      if (!response.ok || !response.body) {
        const detail = await response.text().catch(() => "");
        throw new Error(`Server javob bermadi (${response.status}) ${detail.slice(0, 200)}`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let index;
        while ((index = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, index).trim();
          buffer = buffer.slice(index + 1);
          if (!line) continue;
          let event;
          try { event = JSON.parse(line); } catch { continue; }
          (handlers[event.type] || (() => {}))(event);
        }
      }
    } catch (error) {
      if (error.name === "AbortError") {
        item.stopped = true;
      } else {
        item.error = /fetch|network/i.test(error.message)
          ? "LocalAI serveri bilan aloqa uzildi. Server ishlayotganini tekshiring."
          : error.message;
      }
    } finally {
      clearTyping();
      endThinking();
      endText();
      for (const card of view.approvals.values()) card.remove();
      for (const block of item.blocks) {
        if (block.t === "tool" && block.status === "running") {
          block.status = "stopped";
          block.waiting = false;
          const toolEl = view.toolEls.get(block.id);
          if (toolEl) updateToolView(toolEl, block);
        }
      }
      commitHistory(chat, received, partial);
      item.streaming = false;
      view.content.classList.remove("streaming");
      view.orb.classList.remove("is-busy");
      if (!item.blocks.some((block) => block.t === "text" || block.t === "tool") && !item.error && !item.stopped) {
        item.error = "Javob olinmadi. Qayta urinib ko'ring.";
      }
      if (item.error) showError(view, item.error, chat);
      if (item.stopped) view.content.appendChild(node(`<div class="stopped-note">To'xtatildi</div>`));
      addActions(view, chat);
      state.busy = false;
      state.controller = null;
      chat.updated = Date.now();
      updateSend();
      save();
      renderChatList();
      if (state.stick) scrollToBottom(true);
    }
  }

  function commitHistory(chat, received, partial) {
    const messages = received.slice();
    if (partial.trim()) messages.push({ role: "assistant", content: partial.trim() });
    // Javobi kelmagan vosita chaqiruvlari tarixni buzmasligi uchun olib tashlanadi.
    for (let index = messages.length - 1; index >= 0; index--) {
      const message = messages[index];
      if (message.role !== "assistant" || !message.tool_calls) continue;
      const answered = messages.slice(index + 1).filter((next) => next.role === "tool").length;
      if (answered < message.tool_calls.length) {
        messages.splice(index + 1);
        messages[index] = { role: "assistant", content: message.content || "" };
      }
      break;
    }
    chat.history.push(...messages.filter((message) => message.role !== "assistant" || message.content || message.tool_calls));
  }

  function regenerate(assistantItem) {
    if (state.busy) return;
    const chat = currentChat();
    const index = chat.items.indexOf(assistantItem);
    if (index < 1) return;
    const userItem = chat.items[index - 1];
    if (!userItem || userItem.role !== "user") return;
    chat.items.splice(index - 1);
    renderThread();
    send(userItem.text, userItem.files || [], userItem.historyIndex);
  }

  /* ------------------------------------------------------------ approval */

  const APPROVAL_TITLES = {
    list_directory: "Papkani ko'rishga ruxsat berasizmi?",
    read_file: "Faylni o'qishga ruxsat berasizmi?",
    search_files: "Papka ichida qidirishga ruxsat berasizmi?",
    analyze_table: "Jadvalni tahlil qilishga ruxsat berasizmi?",
  };

  function approvalCard(event) {
    const isWrite = event.access === "write";
    const title = isWrite
      ? (event.exists ? "Fayl ustidan yozishga ruxsat berasizmi?" : "Yangi fayl yaratishga ruxsat berasizmi?")
      : APPROVAL_TITLES[event.name] || "Ruxsat berasizmi?";
    const meta = [event.detail, event.note].filter(Boolean).map(esc).join(" · ");
    const card = node(html`
      <div class="approval${event.sensitive ? " sensitive" : ""}" role="group" aria-label="Ruxsat so'rovi">
        <div class="approval-inner">
          <h4>${icon(isWrite ? "pencil" : "shield")}${esc(title)}</h4>
          <code class="path"></code>
          ${meta ? `<p class="meta">${meta}</p>` : ""}
          ${event.sensitive ? `<div class="warn">${icon("alert")}<span>Bu yerda parol, kalit yoki maxfiy sozlamalar bo'lishi mumkin. Faqat ishonchingiz komil bo'lsa ruxsat bering.</span></div>` : ""}
          ${event.preview ? `<pre></pre>` : ""}
          <div class="actions"></div>
        </div>
      </div>`);
    card.querySelector(".path").textContent = event.path;
    if (event.preview) card.querySelector("pre").textContent = event.preview;
    const actions = card.querySelector(".actions");
    const decide = async (decision, button) => {
      actions.querySelectorAll("button").forEach((item) => { item.disabled = true; });
      button.innerHTML = `<span class="spinner"></span>${button.textContent}`;
      try {
        const response = await fetch("/api/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: event.id, decision }),
        });
        if (!response.ok) throw new Error();
      } catch {
        toast("So'rov muddati o'tgan yoki aloqa uzilgan");
        card.remove();
      }
    };
    const add = (label, decision, cls, iconName, titleText) => {
      const button = node(`<button class="btn ${cls}" type="button">${iconName ? icon(iconName) : ""}${esc(label)}</button>`);
      if (titleText) button.title = titleText;
      button.addEventListener("click", () => decide(decision, button));
      actions.appendChild(button);
    };
    add(isWrite ? "Saqlash" : "Ruxsat berish", "allow", "primary", "check");
    if (!isWrite && event.folder) {
      add("Papkaga doimiy", "allow_folder", "", "folder",
        `Shu suhbat davomida ${event.folder} ichidagi fayllar uchun qayta so'ralmaydi`);
    }
    add("Rad etish", "deny", "ghost", "x");
    return card;
  }

  /* -------------------------------------------------------------- status */

  let statusTimer = null;
  async function refreshStatus(force = false) {
    clearTimeout(statusTimer);
    try {
      const response = await fetch(`/api/status${force ? "?refresh=1" : ""}`);
      state.status = await response.json();
    } catch {
      state.status = { ready: false, ollama: false, server: false, message: "LocalAI serveri bilan aloqa yo'q." };
    }
    applyStatus();
    statusTimer = setTimeout(refreshStatus, state.status.ready ? 30000 : 4000);
  }

  function applyStatus() {
    const status = state.status || {};
    el.statusDot.className = `status-dot ${status.ready ? "ok" : status.ollama ? "wait" : "bad"}`;
    if (status.max_upload) state.maxUpload = status.max_upload;
    const caps = status.capabilities || [];
    el.think.hidden = caps.length > 0 && !caps.includes("thinking");
    if (status.ready) {
      el.banner.hidden = true;
    } else {
      el.banner.innerHTML = `${icon("alert")}<span>${MD.inline(status.message || "Model tayyor emas.")}</span>`;
      const retry = node(`<button class="btn" type="button">${icon("refresh")}Tekshirish</button>`);
      retry.addEventListener("click", () => refreshStatus(true));
      el.banner.appendChild(retry);
      el.banner.hidden = false;
    }
    if (!el.popover.hidden) renderPopover();
  }

  function renderPopover() {
    const status = state.status || {};
    const model = status.model
      ? `${status.model}${status.model !== status.base_model ? ` (${status.base_model})` : ""}`
      : "—";
    el.popover.innerHTML = html`
      <h3><span class="orb" style="--size:18px"></span>LocalAI ${esc(status.version || "")}</h3>
      <dl>
        <dt>Holat</dt><dd>${esc(status.ready ? "Tayyor" : "Tayyor emas")}</dd>
        <dt>Model</dt><dd>${esc(model)}</dd>
        <dt>Ollama</dt><dd>${esc(status.ollama_url || "—")}</dd>
        <dt>Papka</dt><dd>${esc(status.workspace || "~")}</dd>
      </dl>
      <p>${status.private === false
        ? "Model sozlangan Ollama serverida ishlaydi."
        : "Hammasi shu kompyuterda ishlaydi."} Fayl va papkalarga faqat sizning ruxsatingiz bilan kiriladi.</p>`;
    const button = node(`<button class="btn" type="button">${icon("refresh")}Qayta tekshirish</button>`);
    button.addEventListener("click", () => refreshStatus(true));
    el.popover.appendChild(button);
  }

  async function loadSkills() {
    try {
      const response = await fetch("/api/skills");
      state.skills = (await response.json()).skills || [];
    } catch {
      state.skills = [];
    }
  }

  /* -------------------------------------------------------------- events */

  function setupIcons() {
    $("menuBtn").innerHTML = icon("sidebar");
    $("newChatBtn").innerHTML = icon("compose");
    $("sidebarNew").innerHTML = icon("compose");
    $("sidebarClose").innerHTML = icon("x");
    el.attach.innerHTML = icon("paperclip");
    $("sidebarFoot").innerHTML = `${icon("lock")}<span>Suhbatlar faqat shu brauzerda saqlanadi</span>`;
  }

  function setupEvents() {
    el.composer.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
    el.input.addEventListener("input", () => { autosize(); updateSend(); updateSlash(); });
    el.input.addEventListener("keydown", (event) => {
      if (state.slash.open) {
        if (event.key === "ArrowDown") { event.preventDefault(); return moveSlash(1); }
        if (event.key === "ArrowUp") { event.preventDefault(); return moveSlash(-1); }
        if (event.key === "Tab" || (event.key === "Enter" && !event.shiftKey)) { event.preventDefault(); return chooseSlash(state.slash.index); }
        if (event.key === "Escape") { event.preventDefault(); return closeSlash(); }
      }
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        if (!state.busy) submit();
      }
    });
    el.input.addEventListener("blur", () => setTimeout(closeSlash, 120));
    el.input.addEventListener("paste", (event) => {
      const files = event.clipboardData && event.clipboardData.files;
      if (files && files.length) { event.preventDefault(); addFiles(files); }
    });

    el.attach.addEventListener("click", () => el.fileInput.click());
    el.fileInput.addEventListener("change", () => { addFiles(el.fileInput.files); el.fileInput.value = ""; });

    el.think.addEventListener("click", () => {
      state.think = !state.think;
      el.think.classList.toggle("on", state.think);
      el.think.setAttribute("aria-pressed", String(state.think));
      save();
      el.input.focus();
    });
    el.think.classList.toggle("on", state.think);
    el.think.setAttribute("aria-pressed", String(state.think));

    $("menuBtn").addEventListener("click", openSidebar);
    $("sidebarClose").addEventListener("click", closeSidebar);
    $("sidebarNew").addEventListener("click", newChat);
    $("newChatBtn").addEventListener("click", newChat);
    el.scrim.addEventListener("click", closeSidebar);

    $("brandBtn").addEventListener("click", (event) => {
      event.stopPropagation();
      el.popover.hidden = !el.popover.hidden;
      if (!el.popover.hidden) renderPopover();
    });
    document.addEventListener("click", (event) => {
      if (!el.popover.hidden && !el.popover.contains(event.target)) el.popover.hidden = true;
    });

    el.inner.addEventListener("click", async (event) => {
      const button = event.target.closest(".copy-code");
      if (!button) return;
      const code = button.closest(".code-block").querySelector("code").textContent;
      await copyText(code);
      button.classList.add("done");
      button.querySelector("span").textContent = "Nusxalandi";
      setTimeout(() => { button.classList.remove("done"); button.querySelector("span").textContent = "Nusxa"; }, 1500);
    });

    document.addEventListener("keydown", (event) => {
      if (event.defaultPrevented) return;
      const mod = event.ctrlKey || event.metaKey;
      if (mod && event.shiftKey && event.key.toLowerCase() === "o") { event.preventDefault(); newChat(); return; }
      if (event.key === "Escape") {
        if (el.sidebar.classList.contains("open")) closeSidebar();
        else if (!el.popover.hidden) el.popover.hidden = true;
        else if (state.busy) stop();
        return;
      }
      const idle = !document.activeElement || document.activeElement === document.body;
      if (idle && !mod && !event.altKey && event.key.length === 1 && event.key !== " ") el.input.focus();
    });

    let dragDepth = 0;
    const hasFiles = (event) => event.dataTransfer && [...event.dataTransfer.types].includes("Files");
    window.addEventListener("dragenter", (event) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      dragDepth++;
      el.drop.classList.add("show");
    });
    window.addEventListener("dragover", (event) => { if (hasFiles(event)) event.preventDefault(); });
    window.addEventListener("dragleave", (event) => {
      if (!hasFiles(event)) return;
      dragDepth = Math.max(0, dragDepth - 1);
      if (!dragDepth) el.drop.classList.remove("show");
    });
    window.addEventListener("drop", (event) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      dragDepth = 0;
      el.drop.classList.remove("show");
      addFiles(event.dataTransfer.files);
    });
    window.addEventListener("resize", () => { autosize(); setPlaceholder(); });
  }

  function setPlaceholder() {
    el.input.placeholder = window.innerWidth < 640 ? "Xabar yozing…" : "Xabar yozing yoki / bilan ko'nikma tanlang…";
  }

  /* ---------------------------------------------------------------- init */

  load();
  setPlaceholder();
  setupIcons();
  setupEvents();
  renderThread();
  updateSend();
  refreshStatus();
  loadSkills();
  el.input.focus();
})();
