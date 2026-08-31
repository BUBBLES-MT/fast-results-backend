# app/core/email.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    🔥 Email Service using Mailtrap SMTP
    Handles sending emails for password reset, notifications, etc.
    """

    def __init__(self):
        self.smtp_server = settings.MAIL_SERVER
        self.smtp_port = settings.MAIL_PORT
        self.username = settings.MAIL_USERNAME
        self.password = settings.MAIL_PASSWORD
        self.use_tls = settings.MAIL_USE_TLS
        self.use_ssl = settings.MAIL_USE_SSL
        self.from_email = settings.MAIL_DEFAULT_SENDER
        self.from_name = settings.MAILTRAP_FROM_NAME

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML version of email
            text_content: Plain text version (optional)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Add text part
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send email
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.username, self.password)
                    server.sendmail(self.from_email, to_email, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.username, self.password)
                    server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"✅ Email sent to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {str(e)}")
            return False

    def send_password_reset_email(self, to_email: str, reset_token: str, username: str) -> bool:
        """
        Send password reset email with reset link
        
        Args:
            to_email: User's email
            reset_token: Unique reset token
            username: User's name for personalization
        
        Returns:
            bool: True if sent successfully
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Password</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    padding: 40px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #0ea5e9;
                }}
                .header h1 {{
                    color: #0ea5e9;
                    margin: 0;
                    font-size: 24px;
                }}
                .header p {{
                    color: #6b7280;
                    margin: 5px 0 0;
                }}
                .content {{
                    padding: 30px 0;
                    color: #333333;
                }}
                .button-container {{
                    text-align: center;
                    margin: 25px 0;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #0ea5e9, #3b82f6);
                    color: white;
                    padding: 14px 36px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: bold;
                    font-size: 16px;
                }}
                .button:hover {{
                    background: linear-gradient(135deg, #0284c7, #2563eb);
                }}
                .warning {{
                    background-color: #fef3c7;
                    padding: 12px 16px;
                    border-radius: 6px;
                    color: #92400e;
                    font-size: 14px;
                    margin: 15px 0;
                }}
                .footer {{
                    text-align: center;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 12px;
                }}
                .url-box {{
                    background-color: #f3f4f6;
                    padding: 10px;
                    border-radius: 6px;
                    font-size: 12px;
                    color: #374151;
                    word-break: break-all;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 MASI FAST RESULTS</h1>
                    <p>Reset Your Password</p>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>We received a request to reset your password for your <strong>MASI FAST RESULTS</strong> account.</p>
                    
                    <div class="button-container">
                        <a href="{reset_url}" class="button">🔑 Reset Password</a>
                    </div>
                    
                    <div class="warning">
                        ⚠️ This link will expire in <strong>1 hour</strong>.<br>
                        If you didn't request this, please ignore this email.
                    </div>
                    
                    <p style="font-size: 14px; color: #6b7280;">
                        If the button doesn't work, copy and paste this URL into your browser:
                    </p>
                    <div class="url-box">
                        {reset_url}
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 MASI FAST RESULTS. All rights reserved.</p>
                    <p style="color: #9ca3af;">Fast and Accurate Results for Schools</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Reset Your Password - MASI FAST RESULTS
        
        Hello {username},
        
        We received a request to reset your password.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        If you didn't request this, please ignore this email.
        
        ---
        MASI FAST RESULTS - Fast and Accurate Results for Schools
        """
        
        return self.send_email(
            to_email=to_email,
            subject="🔐 Reset Your Password - MASI FAST RESULTS",
            html_content=html_content,
            text_content=text_content
        )

    def send_welcome_email(self, to_email: str, username: str, role: str) -> bool:
        """
        Send welcome email to new user
        
        Args:
            to_email: User's email
            username: User's name
            role: User's role (Teacher, Admin, etc.)
        
        Returns:
            bool: True if sent successfully
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to MASI FAST RESULTS</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    padding: 40px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #0ea5e9;
                }}
                .header h1 {{
                    color: #0ea5e9;
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px 0;
                    color: #333333;
                }}
                .role-badge {{
                    display: inline-block;
                    background: linear-gradient(135deg, #0ea5e9, #3b82f6);
                    color: white;
                    padding: 4px 16px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                .features {{
                    background-color: #f0f9ff;
                    padding: 15px 20px;
                    border-radius: 8px;
                    margin: 15px 0;
                }}
                .features ul {{
                    margin: 5px 0;
                    padding-left: 20px;
                    color: #374151;
                }}
                .features li {{
                    margin: 5px 0;
                }}
                .footer {{
                    text-align: center;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to MASI FAST RESULTS!</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>Welcome to <strong>MASI FAST RESULTS</strong> - the premier school management system for fast and accurate results!</p>
                    
                    <div style="background-color: #f0f9ff; padding: 15px; border-radius: 8px; margin: 15px 0;">
                        <p style="margin: 0; color: #0369a1;">
                            <strong>Your Role:</strong> <span class="role-badge">{role}</span>
                        </p>
                    </div>
                    
                    <div class="features">
                        <p style="font-weight: bold; margin-top: 0;">You can now:</p>
                        <ul>
                            <li>📊 View student results instantly</li>
                            <li>📝 Manage marks and grades</li>
                            <li>📈 Track academic progress</li>
                            <li>📱 Access from any device</li>
                        </ul>
                    </div>
                    
                    <p style="margin-top: 20px;">
                        <a href="{settings.FRONTEND_URL}/login" style="color: #0ea5e9; font-weight: bold;">
                            Login to your account →
                        </a>
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 MASI FAST RESULTS. All rights reserved.</p>
                    <p style="color: #9ca3af;">Fast and Accurate Results for Schools</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to MASI FAST RESULTS!
        
        Hello {username},
        
        Welcome to MASI FAST RESULTS - the premier school management system.
        
        Your Role: {role}
        
        You can now:
        - View student results instantly
        - Manage marks and grades
        - Track academic progress
        - Access from any device
        
        Login: {settings.FRONTEND_URL}/login
        
        ---
        MASI FAST RESULTS - Fast and Accurate Results for Schools
        """
        
        return self.send_email(
            to_email=to_email,
            subject="🎉 Welcome to MASI FAST RESULTS!",
            html_content=html_content,
            text_content=text_content
        )


# ============================================================
# 🔥 SINGLETON INSTANCE
# ============================================================
email_service = EmailService()