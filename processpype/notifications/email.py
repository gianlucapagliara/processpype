"""Email notification channel (SMTP)."""

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from processpype.notifications.base import NotifierBase

logger = logging.getLogger(__name__)


class EmailBot(NotifierBase):
    """SMTP-based email notifier."""

    def __init__(
        self,
        from_address: str,
        host: str = "localhost",
        port: int = 25,
        password: str | None = None,
    ) -> None:
        super().__init__()
        self.from_address = from_address
        self.server: smtplib.SMTP_SSL | smtplib.SMTP
        if password is not None:
            self.server = smtplib.SMTP_SSL(host=host, port=port, timeout=10)
            self.server.login(user=from_address, password=password)
        else:
            self.server = smtplib.SMTP(host=host, port=port, timeout=10)

    def disconnect(self) -> None:
        self.server.quit()

    def send_msg(
        self,
        to_addresses: list[str],
        cc_addresses: list[str],
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
    ) -> None:
        attachments = attachments or []
        header = (
            "To:"
            + ";".join(to_addresses)
            + "\n"
            + "From: "
            + self.from_address
            + "\n"
            + "CC:"
            + ";".join(cc_addresses)
            + "\n"
        )
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message.attach(MIMEText(body_html, "html"))
        for file_path in attachments:
            with open(file_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype=file_path.split(".")[-1])
            attach.add_header(
                "content-disposition", "attachment", filename=file_path.split("\\")[-1]
            )
            message.attach(attach)
        msg = header + message.as_string()
        try:
            self.server.sendmail(self.from_address, to_addresses + cc_addresses, msg)
        except Exception as e:
            logger.error(f"Error sending email: {e}")
