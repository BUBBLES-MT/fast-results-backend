# app/core/email.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
import requests
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# 🔥 MAILTRAP API (Kama POS!)
# ============================================================

def send_email_mailtrap(to_email: str, subject: str, html_content: str):
    """Send email using Mailtrap API - ✅ IMEBORESHA KAMA POS!"""
    try:
        api_token = settings.MAILTRAP_API_TOKEN
        from_email = settings.MAILTRAP_FROM_EMAIL
        from_name = settings.MAILTRAP_FROM_NAME
        
        if not api_token:
            logger.error("❌ MAILTRAP_API_TOKEN not configured!")
            return False
        
        url = "https://send.api.mailtrap.io/api/send"
        
        payload = {
            "from": {"email": from_email, "name": from_name},
            "to": [{"email": to_email}],
            "subject": subject,
            "html": html_content,
            "category": "Password Reset"
        }
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"📧 Sending email via Mailtrap API to: {to_email}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"❌ Mailtrap API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Mailtrap API error: {str(e)}")
        return False


def send_email_smtp(to_email: str, subject: str, html_content: str):
    """Send email using SMTP (Mailtrap) - Kama POS!"""
    try:
        mail_server = settings.MAIL_SERVER
        mail_port = settings.MAIL_PORT
        mail_username = settings.MAIL_USERNAME
        mail_password = settings.MAIL_PASSWORD
        mail_from = settings.MAIL_DEFAULT_SENDER
        
        logger.info(f"📧 SMTP - Server: {mail_server}:{mail_port}")
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = to_email
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(mail_server, mail_port, timeout=30) as server:
            if settings.MAIL_USE_TLS:
                server.starttls()
            
            if mail_username and mail_password:
                server.login(mail_username, mail_password)
            
            server.send_message(msg)
            
        logger.info(f"✅ Email sent via SMTP to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP Authentication Error: {str(e)}")
        return False
        
    except Exception as e:
        logger.error(f"❌ SMTP Error: {str(e)}")
        return False


def send_email(to_email: str, subject: str, html_content: str):
    """Send email - auto chooses Mailtrap API or SMTP (Kama POS!)"""
    
    # 🔥 Kwanza jaribu Mailtrap API
    if settings.MAILTRAP_ENABLED and settings.MAILTRAP_API_TOKEN:
        success = send_email_mailtrap(to_email, subject, html_content)
        if success:
            return True
    
    # 🔥 Kama API haifanyi kazi, tumia SMTP
    logger.info("📧 Falling back to SMTP...")
    return send_email_smtp(to_email, subject, html_content)


# ============================================================
# 🔥 SEND PASSWORD RESET EMAIL (Kama POS!)
# ============================================================

def send_password_reset_email(to_email: str, reset_link: str, username: str):
    """Send password reset email - ✅ MWONEKANO WA KIMATAIFA"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #f0f2f5;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .email-wrapper {{
                max-width: 580px;
                margin: 30px auto;
                background: #ffffff;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 25px 80px rgba(0, 0, 0, 0.06), 0 10px 30px rgba(0, 0, 0, 0.04);
            }}
            .content {{
                padding: 45px 50px 35px;
            }}
            .greeting {{
                font-size: 24px;
                font-weight: 700;
                color: #1a1a2e;
                margin-top: 0;
                margin-bottom: 4px;
                letter-spacing: -0.5px;
            }}
            .greeting-sub {{
                font-size: 14px;
                color: #8b8fa7;
                margin-top: 0;
                margin-bottom: 25px;
                font-weight: 400;
            }}
            .message {{
                font-size: 15px;
                line-height: 1.8;
                color: #4a4f66;
                margin-bottom: 25px;
            }}
            .button-container {{
                text-align: center;
                margin: 32px 0;
            }}
            .reset-button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #ffffff !important;
                font-weight: 600;
                font-size: 16px;
                padding: 16px 48px;
                border-radius: 50px;
                text-decoration: none;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.30);
                transition: all 0.3s ease;
                letter-spacing: 0.3px;
            }}
            .reset-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 14px 40px rgba(102, 126, 234, 0.40);
            }}
            .warning-box {{
                background: #faf5ff;
                border-left: 3px solid #764ba2;
                padding: 16px 20px;
                border-radius: 8px;
                margin: 20px 0 25px;
            }}
            .warning-box strong {{
                color: #4a1a5e;
                font-size: 13px;
            }}
            .warning-box p {{
                margin: 4px 0 0 0;
                color: #6b4a7a;
                font-size: 13px;
            }}
            .divider {{
                border: none;
                height: 1px;
                background: linear-gradient(to right, #eef0f5 0%, transparent 100%);
                margin: 25px 0;
            }}
            .info-text {{
                font-size: 12px;
                color: #b0b4c4;
                line-height: 1.6;
                margin-bottom: 5px;
            }}
            .security-note {{
                background: #f8f9fc;
                padding: 14px 18px;
                border-radius: 10px;
                font-size: 12px;
                color: #5a5f7a;
                margin-top: 20px;
                border: 1px solid #edf0f5;
            }}
            .security-note i {{
                font-style: normal;
                color: #4caf84;
                font-weight: 600;
            }}
            @media only screen and (max-width: 480px) {{
                .content {{
                    padding: 28px 22px 25px;
                }}
                .email-wrapper {{
                    margin: 10px;
                    border-radius: 16px;
                }}
                .greeting {{
                    font-size: 20px;
                }}
                .reset-button {{
                    padding: 14px 30px;
                    font-size: 15px;
                    display: block;
                    text-align: center;
                }}
            }}
        </style>
    </head>
    <body style="background: #f0f2f5; margin: 0; padding: 10px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #f0f2f5; padding: 0; margin: 0;">
            <tr>
                <td align="center">
                    <table width="100%" max-width="580" cellpadding="0" cellspacing="0" border="0" style="max-width: 580px; width: 100%;">
                        <tr>
                            <td align="center" style="padding: 0;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border-radius: 20px 20px 0 0; padding: 0; margin: 0;">
                                    <tr>
                                        <td align="center" style="padding: 38px 20px 32px;">
                                            <div style="display: inline-block; background: rgba(255,255,255,0.05); padding: 10px 26px; border-radius: 14px; backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.06);">
                                                <span style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: 2px;">
                                                    🏫 MASI FAST RESULTS
                                                </span>
                                            </div>
                                            <p style="color: rgba(255,255,255,0.3); font-size: 11px; margin-top: 12px; margin-bottom: 0; letter-spacing: 4px; text-transform: uppercase;">
                                                Fast & Accurate Results
                                            </p>
                                            <div style="width: 50px; height: 2px; background: linear-gradient(to right, #667eea, #764ba2); margin: 10px auto 0; border-radius: 2px;"></div>
                                        </td>
                                    </tr>
                                </table>
                                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #ffffff; border-radius: 0 0 20px 20px; padding: 0; margin: 0;">
                                    <tr>
                                        <td style="padding: 45px 50px 35px;">
                                            <h1 style="font-size: 24px; font-weight: 700; color: #1a1a2e; margin-top: 0; margin-bottom: 4px; letter-spacing: -0.5px;">
                                                Hello, {username}! 👋
                                            </h1>
                                            <p style="font-size: 14px; color: #8b8fa7; margin-top: 0; margin-bottom: 25px; font-weight: 400;">
                                                We received a request to reset your password.
                                            </p>
                                            <p style="font-size: 15px; line-height: 1.8; color: #4a4f66; margin-bottom: 25px;">
                                                Click the button below to create a new password for your account. This link is <strong>valid for 1 hour</strong>.
                                            </p>
                                            <div style="text-align: center; margin: 32px 0;">
                                                <a href="{reset_link}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff !important; font-weight: 600; font-size: 16px; padding: 16px 48px; border-radius: 50px; text-decoration: none; box-shadow: 0 10px 30px rgba(102, 126, 234, 0.30); letter-spacing: 0.3px;">
                                                    🔐 Reset Password
                                                </a>
                                            </div>
                                            <div style="background: #faf5ff; border-left: 3px solid #764ba2; padding: 16px 20px; border-radius: 8px; margin: 20px 0 25px;">
                                                <strong style="color: #4a1a5e; font-size: 13px;">⚠️ Important:</strong>
                                                <p style="margin: 4px 0 0 0; color: #6b4a7a; font-size: 13px;">
                                                    This link will expire in <strong>1 hour</strong>. If you didn't request this, please ignore this email.
                                                </p>
                                            </div>
                                            <hr style="border: none; height: 1px; background: linear-gradient(to right, #eef0f5 0%, transparent 100%); margin: 25px 0;">
                                            <p style="font-size: 12px; color: #b0b4c4; line-height: 1.6; margin-bottom: 5px;">
                                                <strong style="color: #8b8fa7;">🔗 Reset Link:</strong>
                                                <br>
                                                <span style="word-break: break-all; font-size: 11px; color: #6a6f8a;">
                                                    {reset_link}
                                                </span>
                                            </p>
                                            <div style="background: #f8f9fc; padding: 14px 18px; border-radius: 10px; font-size: 12px; color: #5a5f7a; margin-top: 20px; border: 1px solid #edf0f5;">
                                                <i style="font-style: normal; color: #4caf84; font-weight: 600;">✓</i>
                                                <strong style="color: #1a1a2e;">Security Tip:</strong>
                                                <span style="color: #6a6f8a;">Never share this link with anyone.</span>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="background: #0f1117; padding: 35px 50px 30px; border-radius: 0 0 20px 20px;">
                                            <div style="text-align: center;">
                                                <div style="width: 100%; height: 1px; background: linear-gradient(to right, transparent, rgba(255,255,255,0.04), transparent); margin-bottom: 25px;"></div>
                                                <p style="color: rgba(255,255,255,0.3); font-size: 13px; font-weight: 300; margin: 0 0 4px 0; letter-spacing: 2px;">
                                                    MASI FAST RESULTS
                                                </p>
                                                <p style="color: rgba(255,255,255,0.12); font-size: 10px; margin: 0 0 18px 0; letter-spacing: 1px;">
                                                    Fast & Accurate Results for Schools
                                                </p>
                                                <div style="margin-bottom: 18px;">
                                                    <a href="https://bubblesmanage.com" style="color: rgba(255,255,255,0.15); text-decoration: none; font-size: 10px; margin: 0 8px; letter-spacing: 0.5px;">Home</a>
                                                    <span style="color: rgba(255,255,255,0.05);">|</span>
                                                    <a href="mailto:support@bubblesmanage.com" style="color: rgba(255,255,255,0.15); text-decoration: none; font-size: 10px; margin: 0 8px; letter-spacing: 0.5px;">Support</a>
                                                </div>
                                                <p style="color: rgba(255,255,255,0.08); font-size: 9px; margin: 0; letter-spacing: 1px;">
                                                    &copy; 2026 MASI FAST RESULTS. All rights reserved.
                                                </p>
                                                <p style="color: rgba(255,255,255,0.04); font-size: 8px; margin-top: 4px; margin-bottom: 0; letter-spacing: 2px;">
                                                    Built with ❤️ in Tanzania
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    logger.info(f"📧 Sending password reset email to: {to_email}")
    logger.info(f"🔗 Reset link: {reset_link}")
    
    return send_email(to_email, "🔐 Password Reset Request - MASI FAST RESULTS", html_content)


# ============================================================
# 🔥🔥🔥 EMAIL SERVICE CLASS - HII NDIO ILIKOSA! 🔥🔥🔥
# ============================================================

class EmailService:
    """
    🔥 Email Service wrapper for compatibility with auth.py
    Hii ndio inaitwa na app/api/v1/auth/auth.py
    """
    
    def send_password_reset_email(self, to_email: str, reset_token: str, username: str) -> bool:
        """
        Send password reset email using token
        
        Args:
            to_email: Recipient email address
            reset_token: Password reset token
            username: User's name for personalization
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        # 🔥 Build reset link
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # 🔥 Send email
        return send_password_reset_email(to_email, reset_link, username)
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """
        Generic send email method
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content (optional)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        return send_email(to_email, subject, html_content)


# ============================================================
# 🔥🔥🔥 SINGLETON INSTANCE - email_service 🔥🔥🔥
# ============================================================

# 🔥 HII NDIO INATUMIWA NA auth.py!
email_service = EmailService()


# ============================================================
# 🔥 EXPOSE FUNCTIONS FOR DIRECT USE
# ============================================================

__all__ = [
    "email_service",
    "send_email",
    "send_email_mailtrap",
    "send_email_smtp",
    "send_password_reset_email",
    "EmailService"
]