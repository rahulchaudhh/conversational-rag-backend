/**
 * Clean & Simple Chat UI Logic
 * Handles session management, Redis chat history, multi-turn conversation,
 * markdown rendering, document ingestion, and interview booking confirmations.
 */

(() => {
  // State
  let currentSessionId = localStorage.getItem('rag_current_session') || createNewSessionId();
  let sessions = [];
  let currentMessages = [];
  let isSending = false;
  let searchFilter = '';

  // DOM Elements
  const messagesList = document.getElementById('messages-list');
  const chatMessages = document.getElementById('chat-messages');
  const welcomeContainer = document.getElementById('welcome-container');
  const typingIndicator = document.getElementById('typing-indicator');
  const chatForm = document.getElementById('chat-form');
  const messageInput = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-btn');
  const currentSessionDisplay = document.getElementById('current-session-display');
  const sessionsList = document.getElementById('sessions-list');
  const sessionsCountBadge = document.getElementById('sessions-count-badge');
  const searchSessionsInput = document.getElementById('search-sessions-input');
  const refreshSessionsBtn = document.getElementById('refresh-sessions-btn');
  const documentsList = document.getElementById('documents-list');
  const bookingsPreview = document.getElementById('bookings-preview');
  const newChatBtn = document.getElementById('new-chat-btn');
  const clearChatBtn = document.getElementById('clear-chat-btn');
  const exportChatBtn = document.getElementById('export-chat-btn');
  const backendStatusText = document.getElementById('backend-status-text');
  const chatHeaderTitle = document.getElementById('chat-header-title');
  const chatHeaderSubtitle = document.getElementById('chat-header-subtitle');

  // Sidebar mobile elements
  const sidebar = document.getElementById('sidebar');
  const openSidebarBtn = document.getElementById('open-sidebar-btn');
  const closeSidebarBtn = document.getElementById('close-sidebar-btn');

  // Modals & Upload Elements
  const uploadModal = document.getElementById('upload-modal');
  const openUploadModalBtn = document.getElementById('open-upload-modal-btn');
  const headerUploadBtn = document.getElementById('header-upload-btn');
  const attachDocBtn = document.getElementById('attach-doc-btn');
  const closeUploadModalBtn = document.getElementById('close-upload-modal-btn');
  const cancelUploadBtn = document.getElementById('cancel-upload-btn');
  const uploadForm = document.getElementById('upload-form');
  const fileDropzone = document.getElementById('file-dropzone');
  const fileInput = document.getElementById('file-input');
  const selectedFileBadge = document.getElementById('selected-file-badge');
  const selectedFilename = document.getElementById('selected-filename');
  const removeSelectedFile = document.getElementById('remove-selected-file');
  const startUploadBtn = document.getElementById('start-upload-btn');
  const uploadProgress = document.getElementById('upload-progress');
  const uploadStatusText = document.getElementById('upload-status-text');

  // Bookings Modal Elements
  const bookingsModal = document.getElementById('bookings-modal');
  const openBookingsModalBtn = document.getElementById('open-bookings-modal-btn');
  const closeBookingsModalBtn = document.getElementById('close-bookings-modal-btn');
  const closeBookingsFooterBtn = document.getElementById('close-bookings-footer-btn');
  const refreshBookingsBtn = document.getElementById('refresh-bookings-btn');
  const bookingsTableBody = document.getElementById('bookings-table-body');

  let selectedFile = null;

  // Initialize
  function init() {
    setupEventListeners();
    updateSessionUI();
    fetchSessions().then(() => {
      loadHistory(currentSessionId);
    });
    fetchDocuments();
    fetchBookings();
    checkHealth();
  }

  // Session Management
  function createNewSessionId() {
    return 'sess_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now().toString(36);
  }

  async function fetchSessions() {
    try {
      const res = await fetch('/chat/sessions');
      if (res.ok) {
        const redisSessions = await res.json();
        // Merge with current session if not yet in Redis
        const exists = redisSessions.some(s => s.session_id === currentSessionId);
        if (!exists && currentSessionId) {
          redisSessions.unshift({
            session_id: currentSessionId,
            title: 'Current Chat',
            message_count: 0,
            last_message: 'Fresh session'
          });
        }
        sessions = redisSessions;
      }
    } catch (err) {
      console.warn('Could not fetch sessions from Redis:', err);
    }
    renderSessionsList();
  }

  function renderSessionsList() {
    if (!sessionsList) return;
    sessionsList.innerHTML = '';
    const query = searchFilter.trim().toLowerCase();

    const filtered = sessions.filter(s => {
      if (!query) return true;
      return (
        (s.title && s.title.toLowerCase().includes(query)) ||
        (s.session_id && s.session_id.toLowerCase().includes(query)) ||
        (s.last_message && s.last_message.toLowerCase().includes(query))
      );
    });

    if (sessionsCountBadge) {
      sessionsCountBadge.textContent = filtered.length;
    }

    if (filtered.length === 0) {
      sessionsList.innerHTML = query
        ? '<div class="empty-hint">No matching chats</div>'
        : '<div class="empty-hint">No past conversations</div>';
      return;
    }

    filtered.forEach(s => {
      const item = document.createElement('div');
      item.className = `session-item ${s.session_id === currentSessionId ? 'active' : ''}`;
      item.title = `Session: ${s.session_id}`;
      item.onclick = () => switchSession(s.session_id);

      const info = document.createElement('div');
      info.className = 'session-item-info';

      const title = document.createElement('div');
      title.className = 'session-item-title';
      title.textContent = s.title || s.session_id;

      const snippet = document.createElement('div');
      snippet.className = 'session-item-snippet';
      snippet.textContent = s.last_message || `Session ${s.session_id}`;

      info.appendChild(title);
      info.appendChild(snippet);

      const meta = document.createElement('div');
      meta.className = 'session-item-meta';

      if (s.message_count > 0) {
        const pill = document.createElement('span');
        pill.className = 'session-msg-pill';
        pill.textContent = `${s.message_count}`;
        pill.title = `${s.message_count} messages in Redis`;
        meta.appendChild(pill);
      }

      const delBtn = document.createElement('button');
      delBtn.className = 'session-delete-btn';
      delBtn.title = 'Delete from Redis history';
      delBtn.innerHTML = '&times;';
      delBtn.onclick = (e) => deleteSession(s.session_id, e);
      meta.appendChild(delBtn);

      item.appendChild(info);
      item.appendChild(meta);
      sessionsList.appendChild(item);
    });
  }

  async function deleteSession(sessionId, e) {
    if (e) e.stopPropagation();
    if (!confirm(`Clear and delete chat history for ${sessionId}?`)) return;

    try {
      await fetch(`/chat/${sessionId}`, { method: 'DELETE' });
      showToast('Conversation cleared from Redis', 'info');
      sessions = sessions.filter(s => s.session_id !== sessionId);

      if (currentSessionId === sessionId) {
        currentSessionId = createNewSessionId();
        localStorage.setItem('rag_current_session', currentSessionId);
        messagesList.innerHTML = '';
        welcomeContainer.style.display = 'flex';
      }
      updateSessionUI();
      renderSessionsList();
    } catch (err) {
      showToast(`Error deleting session: ${err.message}`, 'error');
    }
  }

  function switchSession(sessionId) {
    if (sessionId === currentSessionId) return;
    currentSessionId = sessionId;
    localStorage.setItem('rag_current_session', currentSessionId);
    updateSessionUI();
    loadHistory(currentSessionId);
    renderSessionsList();
    if (window.innerWidth <= 768) sidebar.classList.remove('open');
  }

  function updateSessionUI() {
    if (currentSessionDisplay) {
      currentSessionDisplay.textContent = currentSessionId;
    }
    const current = sessions.find(s => s.session_id === currentSessionId);
    if (chatHeaderTitle) {
      chatHeaderTitle.textContent = current && current.title && current.title !== 'Current Chat'
        ? current.title
        : 'Assistant';
    }
    if (chatHeaderSubtitle) {
      chatHeaderSubtitle.textContent = `Session: ${currentSessionId}`;
    }
  }

  // Load Session History from Redis via Backend
  async function loadHistory(sessionId) {
    messagesList.innerHTML = '';
    currentMessages = [];
    welcomeContainer.style.display = 'flex';

    try {
      const res = await fetch(`/chat/${sessionId}/history`);
      if (!res.ok) return;
      const data = await res.json();
      const messages = data.messages || [];
      currentMessages = messages;

      if (messages.length > 0) {
        welcomeContainer.style.display = 'none';
        messages.forEach(msg => {
          appendMessage(msg.role, msg.content, false);
        });
        scrollToBottom();
      }
    } catch (err) {
      console.warn('Could not load history for session:', err);
    }
  }

  // Health Check
  async function checkHealth() {
    try {
      const res = await fetch('/health');
      if (res.ok) {
        backendStatusText.textContent = 'Connected';
        const dot = document.querySelector('.status-dot');
        if (dot) dot.className = 'status-dot online';
      }
    } catch {
      backendStatusText.textContent = 'Offline';
      const dot = document.querySelector('.status-dot');
      if (dot) dot.className = 'status-dot offline';
    }
  }

  function updateSendButtonState() {
    if (messageInput.value && messageInput.value.trim().length > 0) {
      sendBtn.classList.add('has-text');
    } else {
      sendBtn.classList.remove('has-text');
    }
  }

  // Message Handling
  async function sendMessage(text) {
    if (!text || !text.trim() || isSending) return;
    const cleanText = text.trim();

    // Hide welcome screen
    welcomeContainer.style.display = 'none';

    // Append user message
    appendMessage('user', cleanText);
    currentMessages.push({ role: 'user', content: cleanText });
    messageInput.value = '';
    adjustTextareaHeight();
    updateSendButtonState();
    scrollToBottom();

    // Set sending state & show indicator
    isSending = true;
    sendBtn.disabled = true;
    typingIndicator.style.display = 'flex';
    scrollToBottom();

    try {
      const response = await fetch('/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: cleanText,
          stream: true
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      if (response.body) {
        typingIndicator.style.display = 'none';

        // Create stream bubble immediately
        const row = document.createElement('div');
        row.className = 'message-row assistant';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar avatar-bot';
        avatar.textContent = 'AI';

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = '<span class="typing-cursor">▊</span>';

        const meta = document.createElement('div');
        meta.className = 'message-meta';
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        meta.innerHTML = `<span>${timeStr}</span>`;

        contentWrapper.appendChild(bubble);
        contentWrapper.appendChild(meta);
        row.appendChild(avatar);
        row.appendChild(contentWrapper);
        messagesList.appendChild(row);
        scrollToBottom();

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullReply = '';
        let bookingInfo = null;
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          // Keep the last partial line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              const jsonStr = trimmed.substring(6);
              try {
                const data = JSON.parse(jsonStr);
                if (data.token) {
                  fullReply += data.token;
                  bubble.innerHTML = renderMarkdown(fullReply);
                  scrollToBottom();
                }
                if (data.booking) {
                  bookingInfo = data.booking;
                }
                if (data.error) {
                  fullReply += `\n\n⚠️ Error: ${data.error}`;
                  bubble.innerHTML = renderMarkdown(fullReply);
                }
              } catch (e) {
                // Partial JSON chunk, ignore
              }
            }
          }
        }

        // Final render after stream completes
        bubble.innerHTML = renderMarkdown(fullReply);
        if (bookingInfo) {
          const bookingCard = createBookingConfirmationCard(`Booking ID: ${bookingInfo.id} Date: ${bookingInfo.date} Time: ${bookingInfo.time}`, bookingInfo.id);
          if (bookingCard) bubble.appendChild(bookingCard);
        } else {
          const bookingMatch = fullReply.match(/Booking ID:\s*(\d+)/i);
          if (bookingMatch) {
            const bookingCard = createBookingConfirmationCard(fullReply, bookingMatch[1]);
            if (bookingCard) bubble.appendChild(bookingCard);
          }
        }

        // Add copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = 'Copy';
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(fullReply);
          copyBtn.textContent = 'Copied!';
          setTimeout(() => (copyBtn.textContent = 'Copy'), 2000);
        };
        meta.appendChild(copyBtn);

        currentMessages.push({ role: 'assistant', content: fullReply });
      } else {
        const text = await response.text();
        typingIndicator.style.display = 'none';
        try {
          const data = JSON.parse(text);
          appendMessage('assistant', data.reply);
          currentMessages.push({ role: 'assistant', content: data.reply });
        } catch {
          appendMessage('assistant', text);
          currentMessages.push({ role: 'assistant', content: text });
        }
      }

      fetchBookings(); // Refresh bookings if an interview was confirmed
      fetchSessions(); // Refresh session list with updated count and snippet
    } catch (err) {
      typingIndicator.style.display = 'none';
      appendMessage('assistant', `⚠️ Sorry, there was an error processing your message: ${err.message}`);
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      messageInput.focus();
      scrollToBottom();
    }
  }

  // Render a single message
  function appendMessage(role, content, shouldScroll = true) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${role === 'user' ? 'avatar-user' : 'avatar-bot'}`;
    avatar.textContent = role === 'user' ? 'You' : 'AI';

    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'message-content-wrapper';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (role === 'user') {
      bubble.textContent = content;
    } else {
      bubble.innerHTML = renderMarkdown(content);

      // Check if message contains interview booking confirmation
      const bookingMatch = content.match(/Booking ID:\s*(\d+)/i);
      if (bookingMatch) {
        const bookingCard = createBookingConfirmationCard(content, bookingMatch[1]);
        if (bookingCard) bubble.appendChild(bookingCard);
      }
    }

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    meta.innerHTML = `<span>${timeStr}</span>`;

    if (role === 'assistant') {
      const copyBtn = document.createElement('button');
      copyBtn.className = 'copy-btn';
      copyBtn.textContent = 'Copy';
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(content);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => (copyBtn.textContent = 'Copy'), 2000);
      };
      meta.appendChild(copyBtn);
    }

    contentWrapper.appendChild(bubble);
    contentWrapper.appendChild(meta);

    if (role === 'user') {
      row.appendChild(contentWrapper);
      row.appendChild(avatar);
    } else {
      row.appendChild(avatar);
      row.appendChild(contentWrapper);
    }

    messagesList.appendChild(row);
    if (shouldScroll) scrollToBottom();
  }

  // Create clean booking appointment card inside message bubble
  function createBookingConfirmationCard(text, bookingId) {
    const card = document.createElement('div');
    card.className = 'booking-card';

    // Parse date and time if present
    const dateMatch = text.match(/\b(202\d-[0-1]\d-[0-3]\d)\b/);
    const timeMatch = text.match(/\b([0-2]?\d:[0-5]\d)\b/);

    card.innerHTML = `
      <div class="booking-card-header">
        <div class="booking-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>Interview Confirmed</span>
        </div>
        <span class="booking-id-tag">ID: #${bookingId}</span>
      </div>
      <div class="booking-grid">
        ${dateMatch ? `<div class="booking-field"><span class="label">Date</span><span class="val">${dateMatch[1]}</span></div>` : ''}
        ${timeMatch ? `<div class="booking-field"><span class="label">Time</span><span class="val">${timeMatch[1]}</span></div>` : ''}
      </div>
    `;
    return card;
  }

  // Safe and clean Markdown-to-HTML parser
  function renderMarkdown(raw) {
    if (!raw) return '';
    let escaped = raw
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Fenced Code Blocks ```code```
    escaped = escaped.replace(/```([a-z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code `code`
    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold **text** or __text__
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/__(.*?)__/g, '<strong>$1</strong>');

    // Italic *text* or _text_
    escaped = escaped.replace(/\*([^\*]+)\*/g, '<em>$1</em>');

    // Bullet points
    const lines = escaped.split('\n');
    let inList = false;
    let htmlLines = [];

    for (let line of lines) {
      const bulletMatch = line.match(/^(\s*)[-*•]\s+(.*)/);
      const numberMatch = line.match(/^(\s*)\d+\.\s+(.*)/);

      if (bulletMatch) {
        if (!inList) {
          htmlLines.push('<ul>');
          inList = 'ul';
        }
        htmlLines.push(`<li>${bulletMatch[2]}</li>`);
      } else if (numberMatch) {
        if (!inList) {
          htmlLines.push('<ol>');
          inList = 'ol';
        }
        htmlLines.push(`<li>${numberMatch[2]}</li>`);
      } else {
        if (inList) {
          htmlLines.push(inList === 'ul' ? '</ul>' : '</ol>');
          inList = false;
        }
        if (line.trim().length > 0) {
          if (line.startsWith('<pre>') || line.endsWith('</pre>')) {
            htmlLines.push(line);
          } else {
            htmlLines.push(`<p>${line}</p>`);
          }
        }
      }
    }
    if (inList) {
      htmlLines.push(inList === 'ul' ? '</ul>' : '</ol>');
    }

    return htmlLines.join('');
  }

  // Export conversation as Markdown
  function exportConversation() {
    if (currentMessages.length === 0) {
      showToast('No messages to export', 'info');
      return;
    }

    let md = `# Conversational RAG Session: ${currentSessionId}\n`;
    md += `Exported on: ${new Date().toLocaleString()}\n\n---\n\n`;

    currentMessages.forEach(msg => {
      const roleLabel = msg.role === 'user' ? '👤 User' : '🤖 Assistant';
      md += `### ${roleLabel}\n\n${msg.content}\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Chat_History_${currentSessionId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Exported conversation as Markdown', 'success');
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function adjustTextareaHeight() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
  }

  // Documents Management
  async function fetchDocuments() {
    try {
      const res = await fetch('/documents/');
      if (!res.ok) return;
      const docs = await res.json();
      renderDocuments(docs);
    } catch (err) {
      documentsList.innerHTML = '<div class="empty-hint">Could not load documents</div>';
    }
  }

  function renderDocuments(docs) {
    if (!documentsList) return;
    documentsList.innerHTML = '';
    if (!docs || docs.length === 0) {
      documentsList.innerHTML = '<div class="empty-hint">No documents indexed yet</div>';
      return;
    }

    docs.forEach(doc => {
      const item = document.createElement('div');
      item.className = 'doc-item';

      const name = document.createElement('span');
      name.className = 'doc-name';
      name.title = doc.filename;
      name.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
        <span>${doc.filename}</span>
      `;

      const badge = document.createElement('span');
      badge.className = 'doc-chunks';
      badge.textContent = `${doc.total_chunks} chunks`;

      item.appendChild(name);
      item.appendChild(badge);
      documentsList.appendChild(item);
    });
  }

  // Bookings Management
  async function fetchBookings() {
    try {
      const res = await fetch('/chat/bookings');
      if (!res.ok) return;
      const bookings = await res.json();
      renderBookingsSidebar(bookings);
      renderBookingsTable(bookings);
    } catch (err) {
      bookingsPreview.innerHTML = '<div class="empty-hint">No bookings yet</div>';
    }
  }

  function renderBookingsSidebar(bookings) {
    if (!bookingsPreview) return;
    bookingsPreview.innerHTML = '';
    if (!bookings || bookings.length === 0) {
      bookingsPreview.innerHTML = '<div class="empty-hint">No bookings yet</div>';
      return;
    }

    // Show latest 3 in sidebar
    bookings.slice(0, 3).forEach(b => {
      const card = document.createElement('div');
      card.className = 'booking-mini-card';
      card.innerHTML = `
        <div class="booking-mini-name">${b.name}</div>
        <div class="booking-mini-date">${b.interview_date || 'TBD'} at ${b.interview_time || 'TBD'}</div>
      `;
      bookingsPreview.appendChild(card);
    });
  }

  function renderBookingsTable(bookings) {
    bookingsTableBody.innerHTML = '';
    if (!bookings || bookings.length === 0) {
      bookingsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No scheduled interviews found.</td></tr>';
      return;
    }

    bookings.forEach(b => {
      const tr = document.createElement('tr');
      const bookedAtStr = b.created_at ? new Date(b.created_at).toLocaleDateString() : '-';
      tr.innerHTML = `
        <td><strong>#${b.id}</strong></td>
        <td>${b.name}</td>
        <td>${b.email}</td>
        <td>${b.interview_date || '-'}</td>
        <td>${b.interview_time || '-'}</td>
        <td>${bookedAtStr}</td>
      `;
      bookingsTableBody.appendChild(tr);
    });
  }

  // Toast notification
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Setup Event Listeners
  function setupEventListeners() {
    // Chat submit
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      sendMessage(messageInput.value);
    });

    // Auto-expand textarea & Enter to submit
    messageInput.addEventListener('input', () => {
      adjustTextareaHeight();
      updateSendButtonState();
    });
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(messageInput.value);
      }
    });

    // Suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const prompt = btn.getAttribute('data-prompt');
        sendMessage(prompt);
      });
    });

    // Search chat history
    if (searchSessionsInput) {
      searchSessionsInput.addEventListener('input', (e) => {
        searchFilter = e.target.value;
        renderSessionsList();
      });
    }

    // Refresh chat history from Redis
    if (refreshSessionsBtn) {
      refreshSessionsBtn.addEventListener('click', () => {
        fetchSessions().then(() => {
          showToast('Refreshed chat history from Redis', 'info');
        });
      });
    }

    // Export current conversation
    if (exportChatBtn) {
      exportChatBtn.addEventListener('click', exportConversation);
    }

    // New Chat Button
    newChatBtn.addEventListener('click', () => {
      currentSessionId = createNewSessionId();
      localStorage.setItem('rag_current_session', currentSessionId);
      currentMessages = [];
      messagesList.innerHTML = '';
      welcomeContainer.style.display = 'flex';
      messageInput.focus();
      updateSessionUI();
      fetchSessions();
      if (window.innerWidth <= 768) sidebar.classList.remove('open');
      showToast('Started a new conversation', 'info');
    });

    // Clear Chat
    clearChatBtn.addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear this conversation?')) {
        await fetch(`/chat/${currentSessionId}`, { method: 'DELETE' }).catch(() => { });
        currentMessages = [];
        messagesList.innerHTML = '';
        welcomeContainer.style.display = 'flex';
        fetchSessions();
        showToast('Conversation cleared', 'info');
      }
    });

    // Copy Session ID on badge click
    if (currentSessionDisplay) {
      currentSessionDisplay.addEventListener('click', () => {
        navigator.clipboard.writeText(currentSessionId);
        showToast('Session ID copied to clipboard', 'info');
      });
    }

    // Sidebar toggle
    if (openSidebarBtn && sidebar) {
      openSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
    }
    if (closeSidebarBtn && sidebar) {
      closeSidebarBtn.addEventListener('click', () => sidebar.classList.remove('open'));
    }

    // Upload Modal toggles
    const openUpload = () => {
      uploadModal.classList.add('open');
      resetUploadForm();
    };
    const closeUpload = () => uploadModal.classList.remove('open');

    if (openUploadModalBtn) openUploadModalBtn.addEventListener('click', openUpload);
    if (headerUploadBtn) headerUploadBtn.addEventListener('click', openUpload);
    if (attachDocBtn) attachDocBtn.addEventListener('click', openUpload);
    if (closeUploadModalBtn) closeUploadModalBtn.addEventListener('click', closeUpload);
    if (cancelUploadBtn) cancelUploadBtn.addEventListener('click', closeUpload);

    // Bookings Modal toggles
    if (openBookingsModalBtn && bookingsModal) {
      openBookingsModalBtn.addEventListener('click', () => {
        bookingsModal.classList.add('open');
        fetchBookings();
      });
    }
    if (closeBookingsModalBtn && bookingsModal) {
      closeBookingsModalBtn.addEventListener('click', () => bookingsModal.classList.remove('open'));
    }
    if (closeBookingsFooterBtn && bookingsModal) {
      closeBookingsFooterBtn.addEventListener('click', () => bookingsModal.classList.remove('open'));
    }
    if (refreshBookingsBtn) {
      refreshBookingsBtn.addEventListener('click', fetchBookings);
    }

    // File Drag & Drop
    fileDropzone.addEventListener('click', () => fileInput.click());
    fileDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      fileDropzone.classList.add('dragover');
    });
    fileDropzone.addEventListener('dragleave', () => fileDropzone.classList.remove('dragover'));
    fileDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      fileDropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelect(e.target.files[0]);
      }
    });

    removeSelectedFile.addEventListener('click', (e) => {
      e.stopPropagation();
      resetUploadFile();
    });

    // Upload Form Submission
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!selectedFile) return;

      const strategy = document.getElementById('chunking-strategy').value;
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('chunking_strategy', strategy);

      startUploadBtn.disabled = true;
      uploadProgress.style.display = 'flex';
      uploadStatusText.textContent = 'Extracting, chunking, and embedding...';

      try {
        const res = await fetch('/documents/upload', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Upload failed with status ${res.status}`);
        }

        const data = await res.json();
        showToast(`Document indexed: ${data.total_chunks} chunks created!`, 'success');
        closeUpload();
        fetchDocuments();

        // Prompt user in chat about the new document
        appendMessage('assistant', `📄 **${data.filename}** has been uploaded and indexed into the vector store (${data.total_chunks} chunks using ${data.chunking_strategy} strategy). You can now ask questions about it!`);
      } catch (err) {
        showToast(`Upload error: ${err.message}`, 'error');
        uploadStatusText.textContent = `Error: ${err.message}`;
      } finally {
        startUploadBtn.disabled = false;
        uploadProgress.style.display = 'none';
      }
    });
  }

  function handleFileSelect(file) {
    const name = file.name.toLowerCase();
    if (!name.endsWith('.pdf') && !name.endsWith('.txt')) {
      showToast('Only .pdf and .txt files are supported', 'error');
      return;
    }
    selectedFile = file;
    selectedFilename.textContent = file.name;
    selectedFileBadge.style.display = 'inline-flex';
    startUploadBtn.disabled = false;
  }

  function resetUploadFile() {
    selectedFile = null;
    fileInput.value = '';
    selectedFileBadge.style.display = 'none';
    startUploadBtn.disabled = true;
  }

  function resetUploadForm() {
    resetUploadFile();
    uploadProgress.style.display = 'none';
    startUploadBtn.disabled = true;
  }

  // Kickoff
  document.addEventListener('DOMContentLoaded', init);
})();
