import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# -------------------------------------------------------
# CONFIG — move these to environment variables before pushing to GitHub
# -------------------------------------------------------
GMAIL_ADDRESS      = 'you@gmail.com'
GMAIL_APP_PASSWORD = 'abcd efgh ijkl mnop'  # myaccount.google.com/apppasswords
FROM_NAME          = 'Website Chatbot'

# -------------------------------------------------------
# LOAD AGENTS CSV
# -------------------------------------------------------
df = pd.read_csv('agents.csv')
df.columns = df.columns.str.strip()


# -------------------------------------------------------
# AGENT LOOKUP
# -------------------------------------------------------
def find_agents_by_county(county: str) -> list[dict]:
    """
    Returns all agents for a given county, sorted by Score descending.
    """
    county_clean = county.strip().lower()
    matches = df[df['County'].str.strip().str.lower() == county_clean].copy()

    if matches.empty:
        return []

    if 'Score' in matches.columns:
        matches = matches.sort_values('Score', ascending=False)

    return matches[['Name', 'Title', 'Specialty', 'County', 'Email', 'Phone']].to_dict(orient='records')


# -------------------------------------------------------
# EMAIL TEMPLATE
# -------------------------------------------------------
def _build_email_html(user_name: str, user_email: str, user_message: str, chat_log: list[dict]) -> str:
    chat_rows = ''
    for msg in chat_log:
        role = msg.get('role', 'unknown').capitalize()
        content = msg.get('content', '').replace('<', '&lt;').replace('>', '&gt;')
        bg = '#f0f4ff' if role == 'User' else '#f9f9f9'
        chat_rows += f"""
        <tr style='background:{bg};'>
            <td style='padding:8px 12px; width:80px; font-weight:bold; color:#555;'>{role}</td>
            <td style='padding:8px 12px; color:#333;'>{content}</td>
        </tr>"""

    return f"""
    <html><body style='font-family:Arial,sans-serif; color:#333; max-width:680px; margin:auto;'>
        <h2 style='color:#2c5f9e;'>📩 New Chat Escalation</h2>
        <p>A visitor could not find the answer they needed and has requested to be contacted.</p>
        <table style='width:100%; border-collapse:collapse; margin-bottom:24px;'>
            <tr><td style='padding:6px; font-weight:bold; width:140px;'>Name:</td><td style='padding:6px;'>{user_name}</td></tr>
            <tr><td style='padding:6px; font-weight:bold;'>Email:</td><td style='padding:6px;'><a href='mailto:{user_email}'>{user_email}</a></td></tr>
            <tr><td style='padding:6px; font-weight:bold;'>Question:</td><td style='padding:6px;'>{user_message}</td></tr>
        </table>
        <h3 style='color:#2c5f9e;'>💬 Full Chat History</h3>
        <table style='width:100%; border-collapse:collapse; border:1px solid #ddd;'>
            {chat_rows}
        </table>
        <p style='margin-top:24px; font-size:12px; color:#999;'>Sent automatically by the website chatbot.</p>
    </body></html>"""


# -------------------------------------------------------
# SEND ESCALATION EMAIL
# -------------------------------------------------------
def send_escalation_email(
    county: str,
    user_name: str,
    user_email: str,
    user_message: str,
    chat_log: list[dict],
    preferred_agent_email: str = None
) -> dict:
    """
    Call this directly from your existing chatbot message handler
    when the user triggers escalation.

    Returns {'success': True/False, 'message': str, 'agent': dict}

    Example usage inside your OpenAI message handler:
        result = send_escalation_email(
            county=detected_county,
            user_name=user_name,
            user_email=user_email,
            user_message=last_user_message,
            chat_log=conversation_history,   # your existing OpenAI messages list
        )
        if result['success']:
            reply = f"I've sent your details to {result['agent']['Name']}. They'll be in touch at {user_email}."
        else:
            reply = "Sorry, something went wrong sending your message. Please try again."
    """
    agents = find_agents_by_county(county)

    if not agents:
        return {'success': False, 'message': f'No agents found for county: {county}', 'agent': None}

    # Use preferred agent if the user picked one, otherwise use top-scored
    if preferred_agent_email:
        agent = next((a for a in agents if a['Email'] == preferred_agent_email), agents[0])
    else:
        agent = agents[0]

    try:
        html = _build_email_html(user_name, user_email, user_message, chat_log)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Chat Escalation from {user_name}'
        msg['From']    = f'{FROM_NAME} <{GMAIL_ADDRESS}>'
        msg['To']      = agent['Email']
        msg.add_header('Reply-To', user_email)  # Agent hits reply → goes to user
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, agent['Email'], msg.as_string())

        return {
            'success': True,
            'message': f"Email sent to {agent['Name']} ({agent['Email']})",
            'agent': agent
        }

    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'message': 'Gmail authentication failed. Check your App Password.', 'agent': None}
    except Exception as e:
        return {'success': False, 'message': str(e), 'agent': None}
