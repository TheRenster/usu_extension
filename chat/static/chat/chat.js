// Chat functionality
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const countyBadge = document.getElementById('countyBadge');
const countyNameSpan = document.getElementById('countyName');
const suggestionsSection = document.getElementById('suggestionsSection');
const mainCategorySelect = document.getElementById('mainCategory');
const subcategorySelect = document.getElementById('subcategory');
const imageInput = document.getElementById('imageInput');

let isSending = false;
let conversationId = null;

// Chat history for context (max 20 messages)
var chatHistory = [];

// Subcategory map from server
var subcategoryMap = {};
(function() {
    var el = document.getElementById('subcategory-map-json');
    if (el && el.textContent) {
        try {
            subcategoryMap = JSON.parse(el.textContent);
        } catch (e) {}
    }
})();

function updateSubcategoryOptions() {
    if (!subcategorySelect || !subcategoryMap) return;
    var main = mainCategorySelect ? mainCategorySelect.value : 'Other';
    var subs = subcategoryMap[main] || subcategoryMap['Other'] || ['Other'];
    subcategorySelect.innerHTML = '';
    subs.forEach(function(s) {
        var opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        subcategorySelect.appendChild(opt);
    });
}
if (mainCategorySelect) {
    mainCategorySelect.addEventListener('change', updateSubcategoryOptions);
}

// Minimum time (ms) to show the loading bubble so it's always visible
var MIN_LOADING_MS = 500;

// Load and display selected county (from localStorage or URL)
(function() {
    var params = new URLSearchParams(window.location.search);
    var countyFromUrl = params.get('county');
    if (countyFromUrl) localStorage.setItem('selected_county', countyFromUrl);
})();
var selectedCounty = localStorage.getItem('selected_county');
if (selectedCounty) {
    countyNameSpan.textContent = selectedCounty;
    countyBadge.style.display = 'inline-block';
}

// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function hideSuggestions() {
    if (suggestionsSection) {
        suggestionsSection.style.display = 'none';
    }
}

function addMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot chat-message'}`;
    if (isUser) {
        messageDiv.textContent = text;
    } else {
        messageDiv.innerHTML = marked.parse(text);
        messageDiv.querySelectorAll('a').forEach(function(a) {
            a.setAttribute('target', '_blank');
            a.setAttribute('rel', 'noopener');
        });

        // Attach feedback controls for Agnes responses
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-controls';

        const labelSpan = document.createElement('span');
        labelSpan.className = 'feedback-label';
        labelSpan.textContent = 'Was this helpful?';

        const yesButton = document.createElement('button');
        yesButton.type = 'button';
        yesButton.className = 'feedback-button';
        yesButton.textContent = 'Yes';

        const noButton = document.createElement('button');
        noButton.type = 'button';
        noButton.className = 'feedback-button';
        noButton.textContent = 'No';

        async function handleFeedback(rating) {
            if (!conversationId) {
                feedbackDiv.textContent = 'Feedback saved for this session.';
                return;
            }
            const csrftoken = getCookie('csrftoken');
            yesButton.disabled = true;
            noButton.disabled = true;
            try {
                await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({
                        conversation_id: conversationId,
                        rating: rating,
                        comment: ''
                    })
                });
                feedbackDiv.textContent = 'Thanks for your feedback.';
            } catch (e) {
                feedbackDiv.textContent = 'Could not send feedback right now.';
            }
        }

        yesButton.addEventListener('click', function () {
            handleFeedback('up');
        });
        noButton.addEventListener('click', function () {
            handleFeedback('down');
        });

        feedbackDiv.appendChild(labelSpan);
        feedbackDiv.appendChild(yesButton);
        feedbackDiv.appendChild(noButton);
        messageDiv.appendChild(feedbackDiv);
    }
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingBubble() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot loading';
    loadingDiv.id = 'loading-bubble';
    loadingDiv.setAttribute('aria-live', 'polite');
    loadingDiv.innerHTML = '<div class="spinner" aria-hidden="true"></div><span class="loading-text">Generating best response…</span>';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return loadingDiv;
}

function removeLoadingBubble() {
    const el = document.getElementById('loading-bubble');
    if (el) el.remove();
}

async function sendMessage() {
    const message = (messageInput && messageInput.value ? messageInput.value.trim() : '') || '';
    const hasImage = imageInput && imageInput.files && imageInput.files.length > 0;
    if (!message && !hasImage) return;
    if (isSending) return;

    isSending = true;
    hideSuggestions();

    const userContent = message || '(User sent a photo for identification)';
    addMessage(userContent, true);
    messageInput.value = '';
    sendButton.disabled = true;
    if (messageInput) messageInput.disabled = true;
    if (imageInput) imageInput.disabled = true;

    addLoadingBubble();
    var loadingShownAt = Date.now();
    chatMessages.scrollTop = chatMessages.scrollHeight;

    function nextFrame() {
        return new Promise(function (resolve) {
            if (typeof requestAnimationFrame !== 'undefined') {
                requestAnimationFrame(resolve);
            } else {
                setTimeout(resolve, 0);
            }
        });
    }
    await nextFrame();
    await nextFrame();

    const county = localStorage.getItem('selected_county') || '';
    const category = mainCategorySelect ? mainCategorySelect.value : '';
    const subcategory = subcategorySelect ? subcategorySelect.value : '';
    const csrftoken = getCookie('csrftoken');

    var body = {
        message: message || '',
        county: county,
        category: category,
        subcategory: subcategory,
        chat_history: chatHistory.slice(-20),
        conversation_id: conversationId
    };

    if (hasImage && imageInput.files[0]) {
        try {
            const base64 = await readFileAsBase64(imageInput.files[0]);
            if (base64) body.image_base64 = base64;
        } catch (e) {
            console.error('Image read failed', e);
        }
        imageInput.value = '';
    }

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if (data.conversation_id) {
            conversationId = data.conversation_id;
            try {
                sessionStorage.setItem('conversation_id', conversationId);
            } catch (e) {
                // Ignore storage errors
            }
        }
        var text = response.ok ? (data.reply || 'Error: No reply received') : (data.error || 'Something went wrong.');

        var elapsed = Date.now() - loadingShownAt;
        var wait = Math.max(0, MIN_LOADING_MS - elapsed);
        await new Promise(function (r) { setTimeout(r, wait); });

        removeLoadingBubble();
        addMessage(text, false);

        chatHistory.push({ role: 'user', content: userContent });
        chatHistory.push({ role: 'assistant', content: text });
        if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
    } catch (e) {
        var elapsed = Date.now() - loadingShownAt;
        var wait = Math.max(0, MIN_LOADING_MS - elapsed);
        await new Promise(function (r) { setTimeout(r, wait); });
        removeLoadingBubble();
        addMessage('Error: Could not connect to server', false);
        chatHistory.push({ role: 'user', content: userContent });
        chatHistory.push({ role: 'assistant', content: 'Error: Could not connect to server' });
    } finally {
        sendButton.disabled = false;
        if (messageInput) messageInput.disabled = false;
        if (imageInput) imageInput.disabled = false;
        isSending = false;
        if (messageInput) messageInput.focus();
    }
}

function readFileAsBase64(file) {
    return new Promise(function (resolve, reject) {
        var reader = new FileReader();
        reader.onload = function() {
            var result = reader.result;
            if (result && result.indexOf('base64,') !== -1) {
                result = result.split('base64,')[1] || '';
            }
            resolve(result || null);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Suggested prompts: click inserts and submits
document.querySelectorAll('.suggestion-pill').forEach(btn => {
    btn.addEventListener('click', function() {
        const question = this.getAttribute('data-question') || this.textContent;
        messageInput.value = question;
        sendMessage();
    });
});

// Event listeners
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Focus input on load
messageInput.focus();

// Restore existing conversation for this tab if available
try {
    const storedConversationId = sessionStorage.getItem('conversation_id');
    if (storedConversationId) {
        conversationId = storedConversationId;
    }
} catch (e) {
    // Ignore storage errors
}

// Initial greeting from Agnes
if (chatMessages) {
    addMessage("Hi! I'm Agnes, your Extension office assistant. Go ahead and ask me a question about your farm, garden, or local Extension resources.", false);
}
