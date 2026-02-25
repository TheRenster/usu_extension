js_snippet = '''
// ============================================================
// Chatbot Escalation — Frontend Integration
// ============================================================

const API_BASE_URL = 'https://YOUR-CLOUD-RUN-URL'; // Replace with your URL

/**
 * Fetch agents for a county and render contact cards.
 * Call this when the bot detects the user didn't get a satisfactory answer.
 */
async function loadAgentContacts(county) {
  const res = await fetch(`${API_BASE_URL}/agents?county=${encodeURIComponent(county)}`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.agents; // Array of {Name, Title, Specialty, Email, Phone}
}

/**
 * Send escalation email with full chat log.
 * chatLog = array of {role: 'user'|'assistant', content: 'string'}
 */
async function sendEscalationEmail({ county, userName, userEmail, userMessage, chatLog, preferredAgentEmail }) {
  const res = await fetch(`${API_BASE_URL}/escalate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      county,
      user_name: userName,
      user_email: userEmail,
      user_message: userMessage,
      chat_log: chatLog,
      preferred_agent_email: preferredAgentEmail || null
    })
  });

  const data = await res.json();

  if (res.ok) {
    // Show success in chat UI
    appendBotMessage(data.message);
  } else {
    appendBotMessage("Sorry, there was a problem sending your message. Please try again.");
    console.error(data.detail);
  }
}

// ---- Example usage inside your bot's "no answer" handler ----

// When bot detects low confidence / user says "that didn\'t help" etc:
async function handleNoAnswerFound(chatLog, detectedCounty) {
  const agents = await loadAgentContacts(detectedCounty);

  if (agents && agents.length > 0) {
    // Render contact cards (your existing feature)
    renderContactCards(agents);

    // Also show email form
    showEmailEscalationForm({
      onSubmit: ({ userName, userEmail, selectedAgentEmail }) => {
        sendEscalationEmail({
          county: detectedCounty,
          userName,
          userEmail,
          userMessage: chatLog[chatLog.length - 2]?.content || '',  // last user message
          chatLog,
          preferredAgentEmail: selectedAgentEmail
        });
      }
    });
  }
}
'''

print(js_snippet)
