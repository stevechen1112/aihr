"""
交易型 Email 寄信服務

支援三種後端：
  - Resend（推薦，API 乾淨、免費 100 封/天）
  - SendGrid
  - SMTP（通用）

所有寄信動作都經由 Celery worker 異步執行，避免阻塞 API 回應。
"""

import logging
from html import escape as _esc
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── 可選依賴 ──
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content

    _HAS_SENDGRID = True
except ImportError:
    _HAS_SENDGRID = False


def _send_via_sendgrid(
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    if not _HAS_SENDGRID:
        logger.error("sendgrid package not installed")
        return False
    try:
        message = Mail(
            from_email=Email(settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body),
        )
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code in (200, 201, 202):
            logger.info(
                "Email sent via SendGrid to %s (status=%d)",
                to_email,
                response.status_code,
            )
            return True
        logger.warning("SendGrid returned status %d for %s", response.status_code, to_email)
        return False
    except Exception as e:
        logger.error("SendGrid send failed: %s", e)
        return False


def _send_via_smtp(
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        import ssl as _ssl

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls(context=_ssl.create_default_context())
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM_ADDRESS, [to_email], msg.as_string())
        logger.info("Email sent via SMTP to %s", to_email)
        return True
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        return False


def _send_via_resend(
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            logger.info("Email sent via Resend to %s (id=%s)", to_email, resp.json().get("id"))
            return True
        logger.warning("Resend returned %d: %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("Resend send failed: %s", e)
        return False


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """
    Send a transactional email using the configured provider.
    Returns True on success.
    """
    provider = (settings.EMAIL_PROVIDER or "").strip().lower()
    if provider == "resend":
        return _send_via_resend(to_email, subject, html_body)
    if provider == "sendgrid":
        return _send_via_sendgrid(to_email, subject, html_body)
    if provider == "smtp":
        return _send_via_smtp(to_email, subject, html_body)
    logger.warning("EMAIL_PROVIDER not configured; email to %s suppressed", to_email)
    return False


# ═══════════════════════════════════════════════════════════
# Email 模板
# ═══════════════════════════════════════════════════════════

_BASE_STYLE = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 560px; margin: 0 auto; padding: 32px 24px;">
"""


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """密碼重設信"""
    link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={reset_token}"
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">重設您的密碼</h2>
    <p>您收到此信件是因為有人對您的 UniHR 帳號提出密碼重設請求。</p>
    <p>請點擊下方按鈕重設密碼（連結 30 分鐘內有效）：</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{link}"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        重設密碼
      </a>
    </p>
    <p style="color:#666; font-size:13px;">如果不是您本人提出的請求，請忽略此信件，您的密碼不會被更改。</p>
</div>"""
    return send_email(to_email, "UniHR — 密碼重設", html)


def send_email_verification(to_email: str, full_name: str, verify_token: str) -> bool:
    """Email 驗證信 — 自助註冊後寄出"""
    safe_name = _esc(full_name)
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={verify_token}"
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">驗證您的電子郵件</h2>
    <p>Hi {safe_name}，</p>
    <p>感謝您註冊 UniHR！請點擊下方按鈕完成電子郵件驗證（連結 24 小時內有效）：</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{link}"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        驗證電子郵件
      </a>
    </p>
    <p style="color:#666; font-size:13px;">如果不是您本人註冊的，請忽略此信件。</p>
</div>"""
    return send_email(to_email, "UniHR — 請驗證您的電子郵件", html)


def send_invitation_email(
    to_email: str,
    invite_token: str,
    tenant_name: str,
    inviter_name: Optional[str] = None,
) -> bool:
    """租戶邀請信"""
    link = f"{settings.FRONTEND_BASE_URL}/accept-invite?token={invite_token}"
    safe_inviter = _esc(inviter_name) if inviter_name else ""
    safe_tenant = _esc(tenant_name)
    invited_by = f"由 {safe_inviter} " if inviter_name else ""
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">您被邀請加入 {safe_tenant}</h2>
    <p>{invited_by}邀請您加入 <strong>{safe_tenant}</strong> 的 UniHR 人資 AI 知識庫。</p>
    <p>請點擊下方按鈕完成帳號設定（連結 7 天內有效）：</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{link}"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        接受邀請
      </a>
    </p>
    <p style="color:#666; font-size:13px;">如果您不認識此組織，請忽略此信件。</p>
</div>"""
    return send_email(to_email, f"UniHR — 邀請加入 {tenant_name}", html)


def send_welcome_email(to_email: str, full_name: str) -> bool:
    """歡迎信"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">歡迎使用 UniHR！</h2>
    <p>Hi {safe_name}，</p>
    <p>您的帳號已成功建立。立即登入開始使用 AI 人資知識庫：</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/login"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        登入 UniHR
      </a>
    </p>
</div>"""
    return send_email(to_email, "歡迎使用 UniHR", html)


def send_onboarding_step1_email(to_email: str, full_name: str, tenant_name: str) -> bool:
    """Onboarding Day 1：快速入門指引"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">🚀 開始使用 UniHR — 3 步驟快速上手</h2>
    <p>Hi {safe_name}，</p>
    <p>歡迎來到 <strong>{_esc(tenant_name)}</strong> 的 UniHR 知識庫！以下是快速上手指引：</p>
    <ol style="line-height:2;">
      <li><strong>上傳第一份文件</strong> — 支援 PDF、Word、Excel 等格式，系統會自動解析建立知識庫。</li>
      <li><strong>試問一個問題</strong> — 到 AI 助理頁面，直接用自然語言提問。</li>
      <li><strong>邀請同事</strong> — 到公司設定頁面新增團隊成員。</li>
    </ol>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/documents"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        前往上傳文件
      </a>
    </p>
</div>"""
    return send_email(to_email, f"UniHR — 3 步驟快速上手 ({tenant_name})", html)


def send_onboarding_step2_email(to_email: str, full_name: str, doc_count: int) -> bool:
    """Onboarding Day 3：文件上傳提醒（若尚未上傳）"""
    safe_name = _esc(full_name)
    if doc_count > 0:
        html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">👍 知識庫已啟用！</h2>
    <p>Hi {safe_name}，</p>
    <p>您的知識庫已有 <strong>{doc_count}</strong> 份文件。試試直接向 AI 助理提問來驗證效果：</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/chat"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        開始提問
      </a>
    </p>
</div>"""
    else:
        html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">📄 還沒上傳文件嗎？</h2>
    <p>Hi {safe_name}，</p>
    <p>您的知識庫目前還沒有文件。上傳公司規章、勞動法規或內部 FAQ，AI 助理就能立即回答相關問題。</p>
    <p>支援格式：PDF、Word、Excel、Markdown、純文字等。</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/documents"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        上傳第一份文件
      </a>
    </p>
</div>"""
    return send_email(
        to_email,
        "UniHR — " + ("知識庫已啟用，試試提問吧！" if doc_count > 0 else "上傳文件開始使用 AI 助理"),
        html,
    )


# ═══════════════════════════════════════════════════════════
# 帳務通知 Email
# ═══════════════════════════════════════════════════════════


def send_payment_success_email(
    to_email: str,
    full_name: str,
    plan: str,
    amount: str,
    trade_no: str,
) -> bool:
    """付款成功通知"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">✅ 付款成功</h2>
    <p>Hi {safe_name}，</p>
    <p>您的 <strong>{_esc(plan)}</strong> 方案付款已完成。</p>
    <table style="width:100%; border-collapse:collapse; margin:16px 0; font-size:14px;">
      <tr><td style="padding:8px 0; color:#666;">交易編號</td><td style="padding:8px 0; font-weight:600;">{_esc(trade_no)}</td></tr>
      <tr><td style="padding:8px 0; color:#666;">金額</td><td style="padding:8px 0; font-weight:600;">{_esc(str(amount))}</td></tr>
    </table>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/subscription"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        查看訂閱狀態
      </a>
    </p>
</div>"""
    return send_email(to_email, f"UniHR — 付款成功（{plan}）", html)


def send_payment_failed_email(to_email: str, full_name: str, plan: str) -> bool:
    """付款失敗通知"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">⚠️ 付款未完成</h2>
    <p>Hi {safe_name}，</p>
    <p>您的 <strong>{_esc(plan)}</strong> 方案付款未成功，請確認付款資訊後重新嘗試。</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/subscription"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        重新訂閱
      </a>
    </p>
    <p style="color:#666; font-size:13px;">如有疑問，請聯繫 {settings.SUPPORT_EMAIL}。</p>
</div>"""
    return send_email(to_email, "UniHR — 付款未完成，請重新嘗試", html)


def send_subscription_expiring_email(
    to_email: str,
    full_name: str,
    plan: str,
    expire_date: str,
) -> bool:
    """訂閱即將到期通知"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">📅 訂閱即將到期</h2>
    <p>Hi {safe_name}，</p>
    <p>您的 <strong>{_esc(plan)}</strong> 方案將於 <strong>{_esc(expire_date)}</strong> 到期。</p>
    <p>到期後將無法使用 AI 問答與文件上傳功能，已上傳的資料會保留 30 天。</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{settings.FRONTEND_BASE_URL}/subscription"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        續約方案
      </a>
    </p>
</div>"""
    return send_email(to_email, f"UniHR — 訂閱將於 {expire_date} 到期", html)


def send_data_export_ready_email(to_email: str, full_name: str, download_link: str) -> bool:
    """個資匯出完成通知"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">📦 資料匯出完成</h2>
    <p>Hi {safe_name}，</p>
    <p>您申請的個人資料匯出已完成，請於 24 小時內下載：</p>
    <p style="text-align:center; margin:24px 0;">
      <a href="{download_link}"
         style="background:#2563eb; color:#fff; padding:12px 32px;
                border-radius:6px; text-decoration:none; font-weight:600;">
        下載資料
      </a>
    </p>
    <p style="color:#666; font-size:13px;">連結將於 24 小時後失效。如非本人操作，請聯繫 {settings.SUPPORT_EMAIL}。</p>
</div>"""
    return send_email(to_email, "UniHR — 個人資料匯出完成", html)


def send_account_deleted_email(to_email: str, full_name: str) -> bool:
    """帳號刪除確認通知"""
    safe_name = _esc(full_name)
    html = f"""{_BASE_STYLE}
    <h2 style="color:#1a1a1a;">帳號已刪除</h2>
    <p>Hi {safe_name}，</p>
    <p>您的 UniHR 帳號及所有相關個人資料已依您的請求刪除。</p>
    <p>此操作不可復原。若您是該租戶的唯一擁有者，租戶資料將依保留政策處理。</p>
    <p style="color:#666; font-size:13px;">如非本人操作，請立即聯繫 {settings.SUPPORT_EMAIL}。</p>
</div>"""
    return send_email(to_email, "UniHR — 帳號已刪除", html)
