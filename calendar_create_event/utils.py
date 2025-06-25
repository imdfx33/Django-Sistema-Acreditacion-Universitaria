from django.conf import settings
from django.core.mail import EmailMultiAlternatives

def send_invitation_email(to_email: str, subject: str, html_content: str):
    """
    Envía un email HTML usando SMTP (configurado en settings.py).
    """
    from_email = settings.DEFAULT_FROM_EMAIL
    msg = EmailMultiAlternatives(subject=subject,
                                 body='',  # texto plano opcional
                                 from_email=from_email,
                                 to=[to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
