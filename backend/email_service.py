# === Email Service (SMTP) ===
"""
Email Service for sending password reset emails via Gmail SMTP.
Production-ready with timeout protection, improved headers, and anti-enumeration safety.
"""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Added: email.utils for RFC 2822 compliant Date header
from email.utils import formatdate, make_msgid

# Configure module logger instead of print statements for production
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed

# Email configuration - set these environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Support multiple variable names to prevent user errors
SMTP_USER = (
    os.getenv("SMTP_USER")
    or os.getenv("SMTP_USERNAME")
    or os.getenv("EMAIL_USER")
    or ""
)
SMTP_PASSWORD = (
    os.getenv("SMTP_PASSWORD")
    or os.getenv("SMTP_PASS")
    or os.getenv("EMAIL_PASSWORD")
    or ""
)
APP_URL = os.getenv("APP_URL", "http://localhost:5173")

# SMTP timeout in seconds
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "30"))


def send_password_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """
    Send password reset email with reset link.
    Returns True if email sent successfully, False otherwise.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        # Detailed Debugging
        logger.warning("SMTP Config Missing:")
        logger.warning(f"- SMTP_USER: {'Set' if SMTP_USER else 'MISSING'}")
        logger.warning(f"- SMTP_PASSWORD: {'Set' if SMTP_PASSWORD else 'MISSING'}")

        # Development fallback
        if os.getenv("DEBUG", "").lower() == "true":
            logger.info(
                f"DEBUG Reset link: {APP_URL}/reset-password?token={reset_token}"
            )
        return False

    reset_link = f"{APP_URL}/reset-password?token={reset_token}"

    # Create email message with multipart/alternative for HTML + plaintext
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "إعادة تعيين كلمة المرور - DENTIX"
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    # Added: RFC 2822 Date header for improved deliverability
    msg["Date"] = formatdate(localtime=True)
    # Added: Unique Message-ID to prevent spam filtering
    msg["Message-ID"] = make_msgid(domain=SMTP_HOST.replace("smtp.", ""))
    # Added: Reply-To header for professional appearance
    msg["Reply-To"] = SMTP_USER
    # Added: X-Mailer header (optional but helps deliverability)
    msg["X-Mailer"] = "DENTIX Password Reset Service"

    # HTML email body - RTL Arabic preserved exactly
    # Added: viewport meta for mobile email clients
    html_body = f"""\
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>إعادة تعيين كلمة المرور</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f4f4; padding: 20px; margin: 0; }}
        .container {{ max-width: 500px; margin: auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .logo {{ text-align: center; font-size: 24px; font-weight: bold; color: #0284c7; margin-bottom: 20px; }}
        h2 {{ color: #1e293b; text-align: center; }}
        p {{ color: #64748b; line-height: 1.8; }}
        .btn {{ display: block; width: 100%; padding: 16px; background: linear-gradient(135deg, #0284c7, #0ea5e9); color: white; text-decoration: none; text-align: center; border-radius: 12px; font-weight: bold; font-size: 16px; margin: 20px 0; box-sizing: border-box; }}
        .btn:hover {{ background: #0369a1; }}
        .warning {{ color: #dc2626; font-size: 12px; }}
        .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🏥 DENTIX</div>
        <h2>إعادة تعيين كلمة المرور</h2>
        <p>مرحباً <strong>{username}</strong>،</p>
        <p>تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك. اضغط على الزر أدناه لإنشاء كلمة مرور جديدة:</p>
        <a href="{reset_link}" class="btn">إعادة تعيين كلمة المرور</a>
        <p class="warning">⚠️ هذا الرابط صالح لمدة 15 دقيقة فقط.</p>
        <p>إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذا البريد.</p>
        <div class="footer">
            <p>DENTIX Management System</p>
        </div>
    </div>
</body>
</html>
"""

    # Plain text alternative for email clients that don't support HTML
    text_body = f"""\
إعادة تعيين كلمة المرور - DENTIX

مرحباً {username}،

تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك.

اضغط على الرابط التالي لإنشاء كلمة مرور جديدة:
{reset_link}

⚠️ هذا الرابط صالح لمدة 15 دقيقة فقط.

إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذا البريد.
"""

    # Attach plain text first, HTML second (email clients prefer last)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # Added: timeout parameter to prevent hanging on HuggingFace
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            # EHLO identifies client to server (improves deliverability)
            server.ehlo()
            server.starttls()
            # Re-identify after TLS handshake (required by RFC)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        # Log success without exposing email address fully
        masked_email = (
            to_email[:3] + "***" + to_email[to_email.index("@") :]
            if "@" in to_email
            else "***"
        )
        logger.info(f"Password reset email sent successfully to {masked_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        # Authentication failed - log securely without exposing credentials
        logger.error("SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD.")
        return False
    except smtplib.SMTPConnectError as e:
        # Connection failed - often firewall/network issue
        logger.error(
            f"SMTP connection failed: {e.smtp_code if hasattr(e, 'smtp_code') else 'unknown'}"
        )
        return False
    except smtplib.SMTPRecipientsRefused:
        # Recipient rejected - don't log full email to prevent enumeration
        logger.warning("Email recipient was refused by server.")
        return False
    except TimeoutError:
        # Timeout - common on serverless platforms like HuggingFace
        logger.error(f"SMTP connection timed out after {SMTP_TIMEOUT} seconds.")
        return False
    except Exception as e:
        # Catch-all for unexpected errors - log type only, not full message
        logger.error(f"Failed to send email: {type(e).__name__}")
        return False
