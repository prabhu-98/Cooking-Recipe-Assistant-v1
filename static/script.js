/**
 * Chef AI — Frontend Logic
 * Handles chat interactions, message rendering, and UI state.
 */

const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatArea = document.getElementById('chatArea');
const messagesContainer = document.getElementById('messagesContainer');
const welcomeScreen = document.getElementById('welcomeScreen');
const clearChatBtn = document.getElementById('clearChatBtn');
const newChatBtn = document.getElementById('newChatBtn');
const sidebar = document.getElementById('sidebar');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebarToggle = document.getElementById('sidebarToggle');
const chatHistory = document.getElementById('chatHistory');

let isProcessing = false;
let chatCount = 0;


// AUTO-RESIZE TEXTAREA

chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});


// SEND MESSAGE

function sendMessage(text) {
    const message = (text || chatInput.value).trim();
    if (!message || isProcessing) return;

    // Hide welcome screen
    welcomeScreen.classList.add('hidden');

    // Add user message
    appendMessage('user', message);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Add to history
    addToHistory(message);

    // Show typing indicator
    const typingEl = appendTypingIndicator();

    // Disable input
    isProcessing = true;
    sendBtn.disabled = true;

    // Send to backend
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    })
    .then(res => res.json())
    .then(data => {
        typingEl.remove();
        if (data.error) {
            appendMessage('assistant', `Error: ${data.error}`);
        } else {
            appendMessage('assistant', data.response);
        }
    })
    .catch(err => {
        typingEl.remove();
        appendMessage('assistant', ` Connection error: ${err.message}. Make sure the server is running.`);
    })
    .finally(() => {
        isProcessing = false;
        sendBtn.disabled = false;
        chatInput.focus();
    });
}


// RENDER MESSAGES

function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🍳';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (role === 'assistant') {
        bubble.innerHTML = formatMarkdown(content);
    } else {
        bubble.textContent = content;
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    messagesContainer.appendChild(msgDiv);

    // Scroll to bottom
    requestAnimationFrame(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    });
}

function appendTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant';
    msgDiv.id = 'typingMessage';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🍳';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `<div class="typing-indicator">
        <span></span><span></span><span></span>
    </div>`;

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    messagesContainer.appendChild(msgDiv);

    chatArea.scrollTop = chatArea.scrollHeight;
    return msgDiv;
}


// MARKDOWN FORMATTING

function formatMarkdown(text) {
    if (!text) return '';

    let html = text
        // Escape HTML
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Headers
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        // Horizontal rule
        .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid var(--border);margin:12px 0;">')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap in paragraph
    html = '<p>' + html + '</p>';

    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<h[123]>)/g, '$1');
    html = html.replace(/(<\/h[123]>)<\/p>/g, '$1');

    return html;
}


// CHAT HISTORY

function addToHistory(message) {
    chatCount++;
    const item = document.createElement('div');
    item.className = 'history-item';
    item.textContent = message.length > 35 ? message.substring(0, 35) + '...' : message;
    item.title = message;
    chatHistory.appendChild(item);
}


// CLEAR / NEW CHAT

function clearChat() {
    messagesContainer.innerHTML = '';
    welcomeScreen.classList.remove('hidden');
    chatHistory.innerHTML = '<div class="history-label">Today</div>';
    chatCount = 0;

    fetch('/api/clear', { method: 'POST' }).catch(() => {});
}

clearChatBtn.addEventListener('click', clearChat);
newChatBtn.addEventListener('click', clearChat);


// SIDEBAR TOGGLE

mobileMenuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
sidebarToggle.addEventListener('click', () => {
    document.body.classList.toggle('sidebar-collapsed');
});

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !mobileMenuBtn.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});


// SUGGESTION CARDS

document.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => {
        const msg = card.getAttribute('data-message');
        sendMessage(msg);
    });
});


// KEYBOARD SHORTCUTS

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', () => sendMessage());

// Focus input on load
chatInput.focus();
