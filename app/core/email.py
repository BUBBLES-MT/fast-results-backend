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
# 🔥 MAILTRAP API (Kama POS HASA!)
# ============================================================

def send_email_mailtrap(to_email: str, subject: str, html_content: str):
    """Send email using Mailtrap API - ✅ KAMA POS HASA!"""
    try:
        # 🔥 DATA ZA POS HASA!
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
    """Send email using SMTP - ✅ KAMA POS HASA!"""
    try:
        # 🔥 DATA ZA POS HASA!
        mail_server = settings.MAIL_SERVER  # live.smtp.mailtrap.io
        mail_port = settings.MAIL_PORT  # 587
        mail_username = settings.MAIL_USERNAME  # api
        mail_password = settings.MAIL_PASSWORD  # 811496902a46029b831bac1d6afe5c74
        mail_from = settings.MAIL_DEFAULT_SENDER  # noreply@bubblesmanage.com
        
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
    """Send email - auto chooses Mailtrap API or SMTP (Kama POS HASA!)"""
    
    # 🔥 Kwanza jaribu Mailtrap API (Kama POS!)
    if settings.MAILTRAP_ENABLED and settings.MAILTRAP_API_TOKEN:
        success = send_email_mailtrap(to_email, subject, html_content)
        if success:
            return True
    
    # 🔥 Kama API haifanyi kazi, tumia SMTP (Kama POS!)
    logger.info("📧 Falling back to SMTP...")
    return send_email_smtp(to_email, subject, html_content)


# ============================================================
# 🔥 SEND PASSWORD RESET EMAIL - PRO MAX ULTRA!
# ============================================================

def send_password_reset_email(to_email: str, reset_link: str, username: str):
    """Send password reset email - ✅ PRO MAX ULTRA!"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Your Password</title>
        <style>
            /* ============================================================
               🔥 BASE STYLES - PRO MAX ULTRA
               ============================================================ */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #f0f4f8;
                margin: 0;
                padding: 20px;
                -webkit-font-smoothing: antialiased;
            }}
            
            /* ============================================================
               🔥 EMAIL WRAPPER - GLASSMORPHISM
               ============================================================ */
            .email-wrapper {{
                max-width: 600px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 24px;
                overflow: hidden;
                box-shadow: 0 30px 80px rgba(14, 165, 233, 0.12), 0 10px 40px rgba(0, 0, 0, 0.04);
                animation: slideUp 0.8s ease-out;
                border: 1px solid rgba(14, 165, 233, 0.06);
            }}
            
            /* ============================================================
               🔥 HEADER - SKY BLUE GRADIENT + ANIMATION
               ============================================================ */
            .email-header {{
                background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 40%, #6366f1 70%, #8b5cf6 100%);
                padding: 45px 30px 40px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .email-header::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.08) 0%, transparent 50%);
                animation: shimmer 4s ease-in-out infinite;
            }}
            
            .email-header::after {{
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(to right, #0ea5e9, #8b5cf6, #ec4899);
                animation: gradientMove 3s ease-in-out infinite;
                background-size: 200% 100%;
            }}
            
            /* 🔥 Floating Particles */
            .particle {{
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.06);
                animation: float 6s ease-in-out infinite;
            }}
            
            .particle:nth-child(1) {{ width: 60px; height: 60px; top: -20px; left: -10px; animation-delay: 0s; }}
            .particle:nth-child(2) {{ width: 80px; height: 80px; bottom: -30px; right: -20px; animation-delay: 2s; }}
            .particle:nth-child(3) {{ width: 40px; height: 40px; top: 50%; left: 20%; animation-delay: 4s; }}
            .particle:nth-child(4) {{ width: 50px; height: 50px; top: 20%; right: 10%; animation-delay: 1s; }}
            
            .email-header .logo {{
                position: relative;
                z-index: 2;
                display: inline-block;
                background: rgba(255, 255, 255, 0.10);
                padding: 12px 28px;
                border-radius: 16px;
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                animation: fadeInDown 0.8s ease-out;
            }}
            
            .email-header .logo span {{
                font-size: 24px;
                font-weight: 800;
                color: #ffffff;
                letter-spacing: 2px;
            }}
            
            .email-header .logo .highlight {{
                color: rgba(255, 255, 255, 0.5);
                font-weight: 300;
                font-size: 14px;
                letter-spacing: 4px;
                margin-left: 6px;
            }}
            
            .email-header .tagline {{
                position: relative;
                z-index: 2;
                color: rgba(255, 255, 255, 0.6);
                font-size: 11px;
                margin-top: 14px;
                letter-spacing: 5px;
                text-transform: uppercase;
                animation: fadeInUp 0.8s ease-out 0.2s both;
            }}
            
            .email-header .divider-line {{
                position: relative;
                z-index: 2;
                width: 60px;
                height: 2px;
                background: rgba(255, 255, 255, 0.2);
                margin: 12px auto 0;
                border-radius: 2px;
            }}
            
            /* ============================================================
               🔥 CONTENT - CLEAN & MODERN
               ============================================================ */
            .email-content {{
                padding: 40px 45px 30px;
                animation: fadeIn 0.8s ease-out 0.3s both;
            }}
            
            .email-content .greeting {{
                font-size: 28px;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 4px;
                letter-spacing: -0.5px;
            }}
            
            .email-content .greeting span {{
                background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            
            .email-content .sub-greeting {{
                font-size: 15px;
                color: #64748b;
                margin-bottom: 25px;
                font-weight: 400;
            }}
            
            .email-content .message {{
                font-size: 16px;
                line-height: 1.8;
                color: #334155;
                margin-bottom: 28px;
            }}
            
            .email-content .message strong {{
                color: #0ea5e9;
                font-weight: 600;
            }}
            
            /* ============================================================
               🔥 BUTTON - ANIMATED
               ============================================================ */
            .button-container {{
                text-align: center;
                margin: 32px 0 28px;
            }}
            
            .reset-button {{
                display: inline-block;
                background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 50%, #8b5cf6 100%);
                color: #ffffff !important;
                font-weight: 600;
                font-size: 17px;
                padding: 16px 52px;
                border-radius: 50px;
                text-decoration: none;
                box-shadow: 0 12px 40px rgba(14, 165, 233, 0.35);
                transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
                letter-spacing: 0.5px;
                position: relative;
                overflow: hidden;
                animation: pulseGlow 2s ease-in-out infinite;
            }}
            
            .reset-button:hover {{
                transform: translateY(-3px) scale(1.02);
                box-shadow: 0 18px 50px rgba(14, 165, 233, 0.45);
            }}
            
            /* 🔥 Button Shimmer */
            .reset-button::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                animation: shimmerButton 3s ease-in-out infinite;
            }}
            
            /* 🔥 Button Glow Pulse */
            .reset-button::after {{
                content: '';
                position: absolute;
                inset: -4px;
                border-radius: 54px;
                background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
                z-index: -1;
                opacity: 0;
                filter: blur(20px);
                transition: opacity 0.4s;
                animation: glowPulse 2s ease-in-out infinite;
            }}
            
            /* ============================================================
               🔥 WARNING BOX - GLASS
               ============================================================ */
            .warning-box {{
                background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
                border-left: 4px solid #0ea5e9;
                padding: 16px 20px;
                border-radius: 12px;
                margin: 22px 0 28px;
                backdrop-filter: blur(10px);
            }}
            
            .warning-box strong {{
                color: #0369a1;
                font-size: 13px;
                display: block;
                margin-bottom: 2px;
            }}
            
            .warning-box p {{
                margin: 0;
                color: #0c4a6e;
                font-size: 14px;
                line-height: 1.5;
            }}
            
            /* ============================================================
               🔥 DIVIDER - ANIMATED
               ============================================================ */
            .divider {{
                border: none;
                height: 1px;
                background: linear-gradient(to right, transparent, #e2e8f0, transparent);
                margin: 25px 0;
                animation: fadeIn 1s ease-out;
            }}
            
            /* ============================================================
               🔥 RESET LINK BOX
               ============================================================ */
            .reset-link-box {{
                background: #f8fafc;
                padding: 14px 18px;
                border-radius: 12px;
                font-size: 13px;
                color: #475569;
                border: 1px solid #e2e8f0;
                margin: 15px 0 20px;
            }}
            
            .reset-link-box strong {{
                color: #0f172a;
                font-weight: 600;
            }}
            
            .reset-link-box .link-text {{
                word-break: break-all;
                font-size: 12px;
                color: #0ea5e9;
                font-weight: 500;
                margin-top: 4px;
                display: block;
            }}
            
            /* ============================================================
               🔥 SECURITY NOTE
               ============================================================ */
            .security-note {{
                background: #f0fdf4;
                padding: 14px 18px;
                border-radius: 12px;
                font-size: 13px;
                color: #166534;
                border: 1px solid #dcfce7;
                margin-top: 20px;
                display: flex;
                align-items: flex-start;
                gap: 10px;
            }}
            
            .security-note .icon {{
                font-size: 18px;
                flex-shrink: 0;
            }}
            
            .security-note strong {{
                color: #14532d;
            }}
            
            .security-note span {{
                color: #15803d;
            }}
            
            /* ============================================================
               🔥 FOOTER - DARK GLASS
               ============================================================ */
            .email-footer {{
                background: #0f172a;
                padding: 35px 45px 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .email-footer::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(to right, transparent, rgba(14, 165, 233, 0.3), transparent);
            }}
            
            .email-footer .brand {{
                color: rgba(255, 255, 255, 0.3);
                font-size: 14px;
                font-weight: 300;
                letter-spacing: 3px;
                text-transform: uppercase;
                margin-bottom: 4px;
            }}
            
            .email-footer .brand-desc {{
                color: rgba(255, 255, 255, 0.12);
                font-size: 10px;
                letter-spacing: 2px;
                margin-bottom: 20px;
            }}
            
            .email-footer .footer-links {{
                margin-bottom: 20px;
            }}
            
            .email-footer .footer-links a {{
                color: rgba(255, 255, 255, 0.15);
                text-decoration: none;
                font-size: 11px;
                margin: 0 10px;
                letter-spacing: 0.5px;
                transition: color 0.3s;
            }}
            
            .email-footer .footer-links a:hover {{
                color: rgba(255, 255, 255, 0.4);
            }}
            
            .email-footer .footer-links span {{
                color: rgba(255, 255, 255, 0.05);
            }}
            
            .email-footer .copyright {{
                color: rgba(255, 255, 255, 0.06);
                font-size: 9px;
                letter-spacing: 1.5px;
            }}
            
            .email-footer .heart {{
                color: #ec4899;
            }}
            
            /* ============================================================
               🔥 ANIMATIONS
               ============================================================ */
            @keyframes slideUp {{
                from {{ opacity: 0; transform: translateY(30px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            @keyframes fadeInDown {{
                from {{ opacity: 0; transform: translateY(-20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            @keyframes fadeInUp {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}
            
            @keyframes shimmer {{
                0%, 100% {{ transform: translate(0, 0) scale(1); }}
                50% {{ transform: translate(10%, 5%) scale(1.1); }}
            }}
            
            @keyframes shimmerButton {{
                0% {{ left: -100%; }}
                50% {{ left: 100%; }}
                100% {{ left: 100%; }}
            }}
            
            @keyframes pulseGlow {{
                0%, 100% {{ box-shadow: 0 12px 40px rgba(14, 165, 233, 0.35); }}
                50% {{ box-shadow: 0 12px 60px rgba(14, 165, 233, 0.55), 0 0 80px rgba(99, 102, 241, 0.2); }}
            }}
            
            @keyframes glowPulse {{
                0%, 100% {{ opacity: 0.3; }}
                50% {{ opacity: 0.6; }}
            }}
            
            @keyframes float {{
                0%, 100% {{ transform: translate(0, 0) scale(1); }}
                33% {{ transform: translate(10px, -15px) scale(1.05); }}
                66% {{ transform: translate(-5px, 10px) scale(0.95); }}
            }}
            
            @keyframes gradientMove {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}
            
            /* ============================================================
               🔥 RESPONSIVE
               ============================================================ */
            @media only screen and (max-width: 480px) {{
                .email-content {{
                    padding: 25px 22px 20px;
                }}
                
                .email-footer {{
                    padding: 25px 22px 20px;
                }}
                
                .email-header {{
                    padding: 30px 20px 25px;
                }}
                
                .email-content .greeting {{
                    font-size: 22px;
                }}
                
                .reset-button {{
                    padding: 14px 30px;
                    font-size: 15px;
                    display: block;
                    text-align: center;
                }}
                
                .email-header .logo span {{
                    font-size: 18px;
                }}
                
                .security-note {{
                    flex-direction: column;
                    align-items: center;
                    text-align: center;
                }}
            }}
        </style>
    </head>
    <body style="background: #f0f4f8; margin: 0; padding: 20px;">
        
        <div class="email-wrapper">
            
            <!-- ============================================================
            🔥 HEADER - SKY BLUE GRADIENT
            ============================================================ -->
            <div class="email-header">
                <!-- Floating Particles -->
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                
                <!-- Logo -->
                <div class="logo">
                    <span>🏫 MASI</span>
                    <span class="highlight">FAST RESULTS</span>
                </div>
                
                <!-- Tagline -->
                <div class="tagline">Fast &amp; Accurate Results for Schools</div>
                <div class="divider-line"></div>
            </div>
            
            <!-- ============================================================
            🔥 CONTENT
            ============================================================ -->
            <div class="email-content">
                
                <!-- Greeting -->
                <h1 class="greeting">
                    Hello, <span>{username}</span>! 👋
                </h1>
                <p class="sub-greeting">We received a request to reset your password.</p>
                
                <!-- Message -->
                <p class="message">
                    Click the button below to create a new password for your account. 
                    This link is <strong>valid for 1 hour</strong>.
                </p>
                
                <!-- Button -->
                <div class="button-container">
                    <a href="{reset_link}" class="reset-button">
                        🔐 Reset Password
                    </a>
                </div>
                
                <!-- Warning Box -->
                <div class="warning-box">
                    <strong>⚠️ Important:</strong>
                    <p>This link will expire in <strong>1 hour</strong>. If you didn't request this, please ignore this email.</p>
                </div>
                
                <!-- Divider -->
                <hr class="divider">
                
                <!-- Reset Link Box -->
                <div class="reset-link-box">
                    <strong>🔗 Reset Link:</strong>
                    <span class="link-text">{reset_link}</span>
                </div>
                
                <!-- Security Note -->
                <div class="security-note">
                    <span class="icon">✅</span>
                    <div>
                        <strong>Security Tip:</strong>
                        <span>Never share this link with anyone. MASI FAST RESULTS will never ask for your password via email.</span>
                    </div>
                </div>
                
            </div>
            
            <!-- ============================================================
            🔥 FOOTER
            ============================================================ -->
            <div class="email-footer">
                <div class="brand">MASI FAST RESULTS</div>
                <div class="brand-desc">Fast &amp; Accurate Results for Schools</div>
                
                <div class="footer-links">
                    <a href="https://bubblesmanage.com">Home</a>
                    <span>|</span>
                    <a href="mailto:support@bubblesmanage.com">Support</a>
                    <span>|</span>
                    <a href="#">Privacy</a>
                    <span>|</span>
                    <a href="#">Terms</a>
                </div>
                
                <div class="copyright">
                    &copy; 2026 MASI FAST RESULTS. All rights reserved.
                </div>
                <div class="copyright" style="margin-top: 4px; color: rgba(255,255,255,0.03);">
                    Built with <span class="heart">❤️</span> in Tanzania
                </div>
            </div>
            
        </div>
        
    </body>
    </html>
    """
    
    logger.info(f"📧 Sending password reset email to: {to_email}")
    logger.info(f"🔗 Reset link: {reset_link}")
    
    return send_email(to_email, "🔐 Reset Your Password - MASI FAST RESULTS", html_content)


# ============================================================
# 🔥🔥🔥 EMAIL SERVICE CLASS - KAMA POS HASA! 🔥🔥🔥
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