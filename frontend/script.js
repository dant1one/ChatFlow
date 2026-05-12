const API_BASE_URL = "http://localhost:8000";
const THEME_KEY = "chat_theme";

const state = {
  token: localStorage.getItem("chat_token"),
  theme: localStorage.getItem(THEME_KEY) || "light",
  me: null,
  users: [],
  groups: [],
  invites: [],
  ws: null,
  authMode: "login",
  selectedChat: null, // {type: "dm"|"group", id: number}
  dmMessages: {},
  groupMessages: {},
  unreadDM: {},
  unreadGroup: {},
  previewDM: {},
  previewGroup: {},
  onlineUsers: new Set(),
  collapsed: { dm: false, groups: false, online: false, offline: false },
  typingTimer: null,
  typingTextTimer: null,
};

const el = {
  authView: document.getElementById("auth-view"),
  chatView: document.getElementById("chat-view"),
  tabLogin: document.getElementById("tab-login"),
  tabRegister: document.getElementById("tab-register"),
  authUsername: document.getElementById("auth-username"),
  authPassword: document.getElementById("auth-password"),
  authSubmit: document.getElementById("auth-submit"),
  authError: document.getElementById("auth-error"),
  meLabel: document.getElementById("me-label"),
  logoutBtn: document.getElementById("logout-btn"),
  themeToggleBtn: document.getElementById("theme-toggle-btn"),
  usersGroups: document.getElementById("users-groups"),
  usersLoading: document.getElementById("users-loading"),
  usersError: document.getElementById("users-error"),
  searchUsersInput: document.getElementById("search-users-input"),
  searchMessagesInput: document.getElementById("search-messages-input"),
  newGroupNameInput: document.getElementById("new-group-name-input"),
  createGroupBtn: document.getElementById("create-group-btn"),
  invitesList: document.getElementById("invites-list"),
  invitesCount: document.getElementById("invites-count"),
  invitesHeader: document.getElementById("invites-header"),
  groupInviteBox: document.getElementById("group-invite-box"),
  groupInviteUsernameInput: document.getElementById("group-invite-username-input"),
  groupInviteBtn: document.getElementById("group-invite-btn"),
  messageInput: document.getElementById("message-input"),
  sendBtn: document.getElementById("send-btn"),
  messagesList: document.getElementById("messages-list"),
  messagesError: document.getElementById("messages-error"),
  messagesLoading: document.getElementById("messages-loading"),
  chatTitle: document.getElementById("chat-title"),
  chatSubtitle: document.getElementById("chat-subtitle"),
  typingIndicator: document.getElementById("typing-indicator"),
};

const showError = (target, message) => {
  target.textContent = message;
  target.classList.remove("hidden");
};
const clearError = (target) => {
  target.textContent = "";
  target.classList.add("hidden");
};

function formatLocalTime(timestamp) {
  if (!timestamp) return "";
  const text = String(timestamp);
  const hasZone = /Z$|[+-]\d{2}:\d{2}$/.test(text);
  const normalized = hasZone ? text : `${text}Z`;
  return new Date(normalized).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { headers, ...options });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Unexpected API error." }));
    throw new Error(detail.detail || "API request failed.");
  }
  if (response.status === 204) return null;
  return response.json();
}

function applyTheme() {
  document.body.classList.toggle("dark", state.theme === "dark");
  el.themeToggleBtn.textContent = state.theme === "dark" ? "Light" : "Dark";
}

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, state.theme);
  applyTheme();
}

function setAuthMode(mode) {
  state.authMode = mode;
  el.tabLogin.classList.toggle("active", mode === "login");
  el.tabRegister.classList.toggle("active", mode === "register");
  el.authSubmit.textContent = mode === "login" ? "Login" : "Register";
}

function showChatView() {
  el.authView.classList.add("hidden");
  el.chatView.classList.remove("hidden");
}
function showAuthView() {
  el.chatView.classList.add("hidden");
  el.authView.classList.remove("hidden");
}

function hashColor(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = text.charCodeAt(i) + ((hash << 5) - hash);
  return `hsl(${Math.abs(hash % 360)}, 65%, 50%)`;
}
const keyDM = (id) => `dm:${id}`;
const keyGroup = (id) => `group:${id}`;
const activeKey = () => (!state.selectedChat ? null : `${state.selectedChat.type}:${state.selectedChat.id}`);

function buildListItem({ id, label, preview, unread, online, active, isGroup }) {
  const li = document.createElement("li");
  li.className = `user-item ${active ? "active" : ""}`;
  li.innerHTML = `
    <div class="avatar" style="background:${hashColor(label)}">
      ${label.slice(0, 2).toUpperCase()}
      ${!isGroup ? `<span class="status-dot ${online ? "online" : "offline"}"></span>` : ""}
    </div>
    <div class="user-main">
      <div class="username">${label}</div>
      <div class="preview">${preview || "No messages yet"}</div>
    </div>
    ${unread > 0 ? `<div class="unread-badge">${unread}</div>` : ""}
  `;
  return li;
}

function renderSection(key, title, items) {
  const section = document.createElement("section");
  section.className = `group ${state.collapsed[key] ? "collapsed" : ""}`;
  const header = document.createElement("button");
  header.className = "group-header";
  header.innerHTML = `<span>${title}</span><span>${items.length}</span>`;
  header.onclick = () => {
    state.collapsed[key] = !state.collapsed[key];
    renderSidebar();
  };
  const list = document.createElement("ul");
  list.className = "group-list";
  items.forEach((item) => list.appendChild(item));
  section.append(header, list);
  return section;
}

function renderSidebar() {
  const q = el.searchUsersInput.value.trim().toLowerCase();
  const others = state.users.filter((u) => u.id !== state.me.id);
  const filteredUsers = others.filter((u) => u.username.toLowerCase().includes(q));
  const filteredGroups = state.groups.filter((g) => g.name.toLowerCase().includes(q));
  const online = filteredUsers.filter((u) => state.onlineUsers.has(u.id));
  const offline = filteredUsers.filter((u) => !state.onlineUsers.has(u.id));

  const dmItems = filteredUsers.map((u) => {
    const li = buildListItem({
      id: u.id,
      label: u.username,
      preview: state.previewDM[u.id] || "",
      unread: state.unreadDM[u.id] || 0,
      online: state.onlineUsers.has(u.id),
      active: activeKey() === keyDM(u.id),
      isGroup: false,
    });
    li.onclick = () => openDM(u);
    return li;
  });

  const groupItems = filteredGroups.map((g) => {
    const li = buildListItem({
      id: g.id,
      label: `${g.name} (${g.participant_count})`,
      preview: state.previewGroup[g.id] || "",
      unread: state.unreadGroup[g.id] || 0,
      online: false,
      active: activeKey() === keyGroup(g.id),
      isGroup: true,
    });
    li.onclick = () => openGroup(g);
    return li;
  });

  const onlineItems = online.map((u) => {
    const li = buildListItem({
      id: u.id,
      label: u.username,
      preview: "Online now",
      unread: 0,
      online: true,
      active: false,
      isGroup: false,
    });
    li.onclick = () => openDM(u);
    return li;
  });

  const offlineItems = offline.map((u) => {
    const li = buildListItem({
      id: u.id,
      label: u.username,
      preview: "Offline",
      unread: 0,
      online: false,
      active: false,
      isGroup: false,
    });
    li.onclick = () => openDM(u);
    return li;
  });

  el.usersGroups.innerHTML = "";
  el.usersGroups.appendChild(renderSection("dm", "Direct Messages", dmItems));
  el.usersGroups.appendChild(renderSection("groups", "Group Chats", groupItems));
  el.usersGroups.appendChild(renderSection("online", "Online Users", onlineItems));
  el.usersGroups.appendChild(renderSection("offline", "Offline Users", offlineItems));
  renderInvitesPanel();
}

function renderInvitesPanel() {
  el.invitesCount.textContent = String(state.invites.length);
  el.invitesList.innerHTML = "";
  state.invites.forEach((invite) => {
    const li = document.createElement("li");
    li.className = "user-item";
    li.innerHTML = `
      <div class="avatar" style="background:${hashColor(invite.group_name)}">${invite.group_name.slice(0, 2).toUpperCase()}</div>
      <div class="user-main">
        <div class="username">${invite.group_name}</div>
        <div class="preview">@${invite.inviter_username} invited you</div>
      </div>
      <div style="display:flex; gap:.3rem">
        <button data-id="${invite.id}" data-action="accept" class="ghost-btn">Ok</button>
        <button data-id="${invite.id}" data-action="decline" class="ghost-btn">No</button>
      </div>
    `;
    li.querySelectorAll("button[data-id]").forEach((btn) => {
      btn.onclick = () => respondInvite(Number(btn.dataset.id), btn.dataset.action === "accept");
    });
    el.invitesList.appendChild(li);
  });
}

function renderMessages(messages = [], isGroup = false) {
  el.messagesList.innerHTML = "";
  messages.forEach((m) => {
    const mine = m.sender_id === state.me.id;
    const div = document.createElement("div");
    div.className = `message-item ${mine ? "sent" : "received"}`;
    const time = formatLocalTime(m.timestamp);
    div.innerHTML = `
      ${isGroup && !mine ? `<span class="sender-name">${m.sender_username || "User"}</span>` : ""}
      <span>${m.content}</span>
      <span class="time">${time}</span>
    `;
    el.messagesList.appendChild(div);
  });
  el.messagesList.scrollTop = el.messagesList.scrollHeight;
}

async function loadUsersAndGroups() {
  el.usersLoading.classList.remove("hidden");
  clearError(el.usersError);
  try {
    const [users, groups, invites] = await Promise.all([
      request("/users"),
      request("/groups"),
      request("/groups/invites/pending"),
    ]);
    state.users = users;
    state.groups = groups;
    state.invites = invites;
    renderSidebar();
  } catch (error) {
    showError(el.usersError, error.message);
  } finally {
    el.usersLoading.classList.add("hidden");
  }
}

async function loadActiveMessages() {
  if (!state.selectedChat) return;
  const search = el.searchMessagesInput.value.trim();
  el.messagesLoading.classList.remove("hidden");
  clearError(el.messagesError);
  try {
    if (state.selectedChat.type === "dm") {
      const id = state.selectedChat.id;
      const path = search
        ? `/messages/search?user_a=${state.me.id}&user_b=${id}&query=${encodeURIComponent(search)}`
        : `/messages/conversation?user_a=${state.me.id}&user_b=${id}`;
      const data = await request(path);
      state.dmMessages[id] = data;
      if (data.length) state.previewDM[id] = data[data.length - 1].content;
      renderMessages(data, false);
    } else {
      const id = state.selectedChat.id;
      const data = await request(`/groups/${id}/messages`);
      const filtered = search ? data.filter((m) => m.content.toLowerCase().includes(search.toLowerCase())) : data;
      state.groupMessages[id] = data;
      if (data.length) state.previewGroup[id] = data[data.length - 1].content;
      renderMessages(filtered, true);
    }
    renderSidebar();
  } catch (error) {
    showError(el.messagesError, error.message);
  } finally {
    el.messagesLoading.classList.add("hidden");
  }
}

function openDM(user) {
  state.selectedChat = { type: "dm", id: user.id };
  state.unreadDM[user.id] = 0;
  el.chatTitle.textContent = `Conversation with ${user.username}`;
  el.chatSubtitle.textContent = state.onlineUsers.has(user.id) ? "Online" : "Offline";
  el.groupInviteBox.classList.add("hidden");
  renderSidebar();
  loadActiveMessages();
}

function openGroup(group) {
  state.selectedChat = { type: "group", id: group.id };
  state.unreadGroup[group.id] = 0;
  el.chatTitle.textContent = group.name;
  el.chatSubtitle.textContent = `${group.participant_count} participants`;
  el.groupInviteBox.classList.remove("hidden");
  renderSidebar();
  loadActiveMessages();
}

async function sendMessage() {
  const content = el.messageInput.value.trim();
  if (!content || !state.selectedChat) return;
  try {
    if (state.selectedChat.type === "dm") {
      await request("/messages", {
        method: "POST",
        body: JSON.stringify({ receiver_id: state.selectedChat.id, content }),
      });
    } else {
      await request(`/groups/${state.selectedChat.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
    }
    el.messageInput.value = "";
    await loadActiveMessages();
  } catch (error) {
    showError(el.messagesError, error.message);
  }
}

async function inviteToCurrentGroup() {
  if (!state.selectedChat || state.selectedChat.type !== "group") return;
  const username = el.groupInviteUsernameInput.value.trim();
  if (!username) return;
  try {
    await request(`/groups/${state.selectedChat.id}/invites`, {
      method: "POST",
      body: JSON.stringify({ username }),
    });
    el.groupInviteUsernameInput.value = "";
  } catch (error) {
    showError(el.messagesError, error.message);
  }
}

async function respondInvite(inviteId, accept) {
  try {
    await request(`/groups/invites/${inviteId}/${accept ? "accept" : "decline"}`, { method: "POST" });
    await loadUsersAndGroups();
  } catch (error) {
    showError(el.usersError, error.message);
  }
}

function sendTypingEvent() {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN || !state.selectedChat) return;
  clearTimeout(state.typingTimer);
  state.typingTimer = setTimeout(() => {
    if (state.selectedChat.type === "dm") {
      state.ws.send(JSON.stringify({ type: "typing_dm", receiver_id: state.selectedChat.id }));
    } else {
      state.ws.send(JSON.stringify({ type: "typing_group", group_id: state.selectedChat.id }));
    }
  }, 120);
}

function showTyping(text) {
  el.typingIndicator.textContent = text;
  el.typingIndicator.classList.remove("hidden");
  clearTimeout(state.typingTextTimer);
  state.typingTextTimer = setTimeout(() => el.typingIndicator.classList.add("hidden"), 1400);
}

function handleIncomingDM(msg) {
  const partnerId = msg.sender_id === state.me.id ? msg.receiver_id : msg.sender_id;
  state.previewDM[partnerId] = msg.content;
  if (activeKey() === keyDM(partnerId)) {
    loadActiveMessages();
  } else if (msg.sender_id !== state.me.id) {
    state.unreadDM[partnerId] = (state.unreadDM[partnerId] || 0) + 1;
  }
  renderSidebar();
}

function handleIncomingGroup(msg) {
  state.previewGroup[msg.group_id] = msg.content;
  if (activeKey() === keyGroup(msg.group_id)) {
    loadActiveMessages();
  } else if (msg.sender_id !== state.me.id) {
    state.unreadGroup[msg.group_id] = (state.unreadGroup[msg.group_id] || 0) + 1;
  }
  renderSidebar();
}

function connectWebSocket() {
  if (!state.me) return;
  if (state.ws) state.ws.close();
  const wsBase = API_BASE_URL.replace("http", "ws");
  state.ws = new WebSocket(`${wsBase}/ws/${state.me.id}?token=${encodeURIComponent(state.token)}`);
  state.ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "presence_snapshot") {
      state.onlineUsers = new Set(payload.online_user_ids || []);
      state.onlineUsers.add(state.me.id);
      renderSidebar();
      return;
    }
    if (payload.type === "presence") {
      if (payload.online) state.onlineUsers.add(payload.user_id);
      else state.onlineUsers.delete(payload.user_id);
      renderSidebar();
      return;
    }
    if (payload.type === "new_message") {
      handleIncomingDM(payload.message);
      return;
    }
    if (payload.type === "new_group_message") {
      handleIncomingGroup(payload.message);
      return;
    }
    if (payload.type === "group_invite") {
      state.invites = [payload.invite, ...state.invites.filter((i) => i.id !== payload.invite.id)];
      renderInvitesPanel();
      return;
    }
    if (payload.type === "group_invite_response") {
      loadUsersAndGroups();
      return;
    }
    if (payload.type === "typing_dm" && activeKey() === keyDM(payload.sender_id)) {
      const user = state.users.find((u) => u.id === payload.sender_id);
      showTyping(`${user ? user.username : "Someone"} is typing...`);
    }
    if (payload.type === "typing_group" && activeKey() === keyGroup(payload.group_id)) {
      const user = state.users.find((u) => u.id === payload.sender_id);
      showTyping(`${user ? user.username : "Someone"} is typing...`);
    }
  };
  state.ws.onopen = () => state.ws.send("connected");
}

async function createGroup() {
  const name = el.newGroupNameInput.value.trim();
  if (!name) return;
  try {
    await request("/groups", { method: "POST", body: JSON.stringify({ name, member_ids: [] }) });
    el.newGroupNameInput.value = "";
    await loadUsersAndGroups();
  } catch (error) {
    showError(el.usersError, error.message);
  }
}

async function authenticate() {
  const username = el.authUsername.value.trim();
  const password = el.authPassword.value.trim();
  if (!username || !password) return showError(el.authError, "Username and password are required.");
  clearError(el.authError);
  try {
    const endpoint = state.authMode === "login" ? "/auth/login" : "/auth/register";
    const data = await request(endpoint, { method: "POST", body: JSON.stringify({ username, password }) });
    state.token = data.token;
    state.me = data.user;
    localStorage.setItem("chat_token", state.token);
    el.meLabel.textContent = `Logged in as @${state.me.username}`;
    showChatView();
    await loadUsersAndGroups();
    connectWebSocket();
  } catch (error) {
    showError(el.authError, error.message);
  }
}

async function restoreSession() {
  if (!state.token) return false;
  try {
    state.me = await request("/auth/me");
    el.meLabel.textContent = `Logged in as @${state.me.username}`;
    showChatView();
    await loadUsersAndGroups();
    connectWebSocket();
    return true;
  } catch {
    localStorage.removeItem("chat_token");
    state.token = null;
    return false;
  }
}

function logout() {
  if (state.ws) state.ws.close();
  state.token = null;
  state.me = null;
  localStorage.removeItem("chat_token");
  showAuthView();
}

window.addEventListener("beforeunload", () => {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) state.ws.close(1000, "tab closed");
});

function bindEvents() {
  el.tabLogin.onclick = () => setAuthMode("login");
  el.tabRegister.onclick = () => setAuthMode("register");
  el.authSubmit.onclick = authenticate;
  el.logoutBtn.onclick = logout;
  el.themeToggleBtn.onclick = toggleTheme;
  el.searchUsersInput.oninput = renderSidebar;
  el.searchMessagesInput.oninput = () => loadActiveMessages();
  el.createGroupBtn.onclick = createGroup;
  el.groupInviteBtn.onclick = inviteToCurrentGroup;
  el.invitesHeader.onclick = () => {
    el.invitesList.classList.toggle("hidden");
  };
  el.sendBtn.onclick = sendMessage;
  el.messageInput.oninput = sendTypingEvent;
  el.messageInput.onkeydown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };
}

async function bootstrap() {
  applyTheme();
  bindEvents();
  setAuthMode("login");
  const restored = await restoreSession();
  if (!restored) showAuthView();
}

bootstrap();
