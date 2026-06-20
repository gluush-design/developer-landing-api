"""Шаблоны писем (HTML + текст).

Весь пользовательский ввод экранируется через html.escape — защита от
HTML/injection в письме.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

from app.schemas.contact import AIAnalysis, ContactRequest


@dataclass
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str


_SENTIMENT_LABEL = {
    "positive": "😊 Позитивная",
    "neutral": "😐 Нейтральная",
    "negative": "😟 Негативная",
}
_PRIORITY_LABEL = {"high": "🔴 Высокий", "normal": "🟡 Обычный", "low": "⚪ Низкий"}
_CATEGORY_LABEL = {
    "collaboration": "Сотрудничество",
    "hiring": "Вакансия / наём",
    "project_inquiry": "Заказ проекта",
    "support": "Вопрос / поддержка",
    "spam": "Спам",
    "other": "Прочее",
}


def build_owner_email(
    owner_email: str, payload: ContactRequest, analysis: AIAnalysis
) -> EmailMessage:
    """Письмо владельцу сайта — заявка + результат AI-анализа."""
    name = escape(payload.name)
    email = escape(str(payload.email))
    phone = escape(payload.phone)
    comment = escape(payload.comment)
    category = _CATEGORY_LABEL.get(analysis.category.value, analysis.category.value)
    sentiment = _SENTIMENT_LABEL.get(analysis.sentiment.value, analysis.sentiment.value)
    priority = _PRIORITY_LABEL.get(analysis.priority.value, analysis.priority.value)
    summary = escape(analysis.summary)
    reply = escape(analysis.suggested_reply)

    subject = f"[{category}] Новое обращение от {payload.name}"

    text_body = (
        f"Новое обращение с лендинга\n"
        f"==========================\n"
        f"Имя: {payload.name}\n"
        f"Email: {payload.email}\n"
        f"Телефон: {payload.phone}\n\n"
        f"Сообщение:\n{payload.comment}\n\n"
        f"--- AI-анализ ({analysis.provider}) ---\n"
        f"Категория: {category}\n"
        f"Тональность: {analysis.sentiment.value} ({analysis.sentiment_score})\n"
        f"Приоритет: {analysis.priority.value}\n"
        f"Резюме: {analysis.summary}\n\n"
        f"Черновик ответа:\n{analysis.suggested_reply}\n"
    )

    html_body = f"""\
<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#1a1a2e">
  <h2 style="color:#0f3460">📨 Новое обращение с лендинга</h2>
  <table style="width:100%;border-collapse:collapse">
    <tr><td style="padding:6px;font-weight:bold">Имя</td><td style="padding:6px">{name}</td></tr>
    <tr><td style="padding:6px;font-weight:bold">Email</td><td style="padding:6px"><a href="mailto:{email}">{email}</a></td></tr>
    <tr><td style="padding:6px;font-weight:bold">Телефон</td><td style="padding:6px">{phone}</td></tr>
  </table>
  <h3 style="color:#0f3460">Сообщение</h3>
  <p style="background:#f3f4f8;padding:12px;border-radius:8px;white-space:pre-wrap">{comment}</p>
  <h3 style="color:#0f3460">🤖 AI-анализ <small style="color:#888">({escape(analysis.provider)})</small></h3>
  <ul style="line-height:1.7">
    <li><b>Категория:</b> {category}</li>
    <li><b>Тональность:</b> {sentiment} ({analysis.sentiment_score})</li>
    <li><b>Приоритет:</b> {priority}</li>
    <li><b>Резюме:</b> {summary}</li>
  </ul>
  <h3 style="color:#0f3460">✍️ Черновик ответа</h3>
  <p style="background:#eef6ff;padding:12px;border-radius:8px;border-left:4px solid #0f3460;white-space:pre-wrap">{reply}</p>
</div>"""

    return EmailMessage(owner_email, subject, text_body, html_body)


def build_user_email(payload: ContactRequest, analysis: AIAnalysis) -> EmailMessage:
    """Письмо-подтверждение пользователю (копия обращения + ответ)."""
    name = escape(payload.name)
    comment = escape(payload.comment)
    reply = escape(analysis.suggested_reply)
    subject = "Мы получили ваше обращение"

    text_body = (
        f"Здравствуйте, {payload.name}!\n\n"
        f"{analysis.suggested_reply}\n\n"
        f"Копия вашего сообщения:\n«{payload.comment}»\n\n"
        f"С уважением,\nкоманда лендинга\n"
    )

    html_body = f"""\
<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#1a1a2e">
  <h2 style="color:#0f3460">Спасибо за обращение, {name}!</h2>
  <p style="font-size:15px;line-height:1.6">{reply}</p>
  <h4 style="color:#0f3460">Копия вашего сообщения</h4>
  <blockquote style="background:#f3f4f8;padding:12px;border-radius:8px;
       border-left:4px solid #0f3460;white-space:pre-wrap;margin:0">{comment}</blockquote>
  <p style="color:#888;font-size:13px;margin-top:24px">
    Это автоматическое подтверждение. Мы свяжемся с вами в ближайшее время.</p>
</div>"""

    return EmailMessage(str(payload.email), subject, text_body, html_body)
