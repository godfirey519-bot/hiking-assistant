"""邮件发送服务（SMTP，标准库 smtplib）。

生产模式下 forgot-password 通过本服务发送真实重置邮件；
SMTP 未配置或发送失败时抛出带明确信息的异常，绝不静默假装"已发送"。
"""
import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailNotConfiguredError(Exception):
    """SMTP 未配置"""


class EmailSendError(Exception):
    """邮件发送失败"""


def _build_reset_email(to_email: str, reset_token: str) -> MIMEText:
    settings = get_settings()
    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={reset_token}"
    subject = "【徒步助手】密码重置"
    body = f"""你好：

你刚刚在徒步助手发起了密码重置请求。请在 30 分钟内点击以下链接设置新密码：

{reset_url}

如果这不是你本人的操作，请忽略此邮件，你的密码不会发生变化。

—— 徒步助手
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    sender = settings.smtp_from or settings.smtp_user
    msg["From"] = formataddr(("徒步助手", sender))
    msg["To"] = to_email
    return msg


def send_reset_email(to_email: str, reset_token: str) -> None:
    """发送密码重置邮件。SMTP 未配置或发送失败时抛出明确异常。"""
    settings = get_settings()
    if not settings.smtp_host:
        raise EmailNotConfiguredError("SMTP 未配置（smtp_host 为空），无法发送重置邮件")

    sender = settings.smtp_from or settings.smtp_user
    if not sender:
        raise EmailNotConfiguredError("SMTP 发件人未配置（smtp_user / smtp_from 均为空）")

    msg = _build_reset_email(to_email, reset_token)

    try:
        if settings.smtp_use_tls:
            # 显式 TLS（STARTTLS，常见于 587 端口）
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(sender, [to_email], msg.as_string())
        else:
            # SSL 直连（常见于 465 端口）
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(sender, [to_email], msg.as_string())
        logger.info(f"重置邮件已发送至 {to_email}")
    except EmailNotConfiguredError:
        raise
    except Exception as exc:  # smtplib 各类网络/认证错误
        logger.exception("重置邮件发送失败")
        raise EmailSendError(f"邮件发送失败: {exc}") from exc
