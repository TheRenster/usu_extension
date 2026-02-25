// ============================================================
// Chatbot Escalation — Frontend
// No separate API needed. When the user submits the escalation
// form, it sends a normal chat message with a special flag that
// your Python backend detects and routes to send_escalation_email().
// ============================================================


/**
 * Call this when the bot determines the user didn't get a useful answer.
 * Renders county-specific contact cards + an optional email form.
 *
 * @param {Array} agents  - Array of agent objects from your bot's county lookup
 *                          [{Name, Title, Specialty, Email, Phone}, ...]
 * @param {Array} chatLog - Current conversation [{role, content}, ...]
 * @param {string} county - Detected county string
 */
function showEscalationOptions(agents, chatLog, county) {
  // --- Render contact cards (your existing feature) ---
  renderContactCards(agents);

  // --- Render email escalation form below the cards ---
  const form = document.createElement('div');
  form.className = 'escalation-form';
  form.innerHTML = `
    <p>Want an agent to contact you directly? Fill in your details below:</p>

    <input id="esc-name"  type="text"  placeholder="Your name"  />
    <input id="esc-email" type="email" placeholder="Your email" />

    ${agents.length > 1 ? `
    <select id="esc-agent">
      ${agents.map(a => `<option value="${a.Email}">${a.Name} — ${a.Specialty}</option>`).join('')}
    </select>` : ''}

    <button id="esc-submit">Send my details to an agent</button>
    <p id="esc-status" style="display:none;"></p>
  `;

  // Append form into your chat UI (adjust selector to match your markup)
  document.querySelector('#chat-messages').appendChild(form);

  // --- Handle submit ---
  document.getElementById('esc-submit').addEventListener('click', () => {
    const userName  = document.getElementById('esc-name').value.trim();
    const userEmail = document.getElementById('esc-email').value.trim();
    const agentEmailEl = document.getElementById('esc-agent');
    const preferredAgent = agentEmailEl ? agentEmailEl.value : agents[0].Email;

    if (!userName || !userEmail) {
      showEscStatus('Please enter your name and email.', 'error');
      return;
    }

    // Disable button to prevent double-submit
    document.getElementById('esc-submit').disabled = true;
    showEscStatus('Sending...', 'info');

    // Send as a structured message through your existing chat endpoint.
    // Your Python backend checks for the __escalation__ flag and calls
    // send_escalation_email() instead of sending to OpenAI.
    sendChatMessage({
      __escalation__: true,
      county:         county,
      user_name:      userName,
      user_email:     userEmail,
      user_message:   getLastUserMessage(chatLog),
      chat_log:       chatLog,
      preferred_agent_email: preferredAgent
    });
  });
}


// ---- Helper: show status message under the form ----
function showEscStatus(msg, type) {
  const el = document.getElementById('esc-status');
  el.textContent = msg;
  el.style.display = 'block';
  el.style.color = type === 'error' ? '#c0392b' : '#27ae60';
}


// ---- Helper: get the last message the user sent ----
function getLastUserMessage(chatLog) {
  const userMessages = chatLog.filter(m => m.role === 'user');
  return userMessages.length ? userMessages[userMessages.length - 1].content : '';
}
