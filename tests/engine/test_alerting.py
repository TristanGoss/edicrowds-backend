from smtplib import SMTPResponseException
from unittest.mock import MagicMock, patch

from engine.alerting import alert_via_email


def test_alert_via_email_sends_message():
    test_alert = 'Test alert'
    test_recipient = 'test@example.com'

    with patch('engine.alerting.smtplib.SMTP_SSL') as mock_smtp:
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        alert_via_email(test_alert, destination_email=test_recipient)

        # Assert login was called with correct credentials
        mock_smtp_instance.login.assert_called_once()
        args, _ = mock_smtp_instance.login.call_args
        assert '@' in args[0]  # crude check to ensure it's an email
        assert isinstance(args[1], str)

        # Assert message was sent
        mock_smtp_instance.send_message.assert_called_once()
        sent_msg = mock_smtp_instance.send_message.call_args[0][0]
        assert test_alert in sent_msg.get_content()
        assert sent_msg['To'] == test_recipient
        assert sent_msg['Subject'] == 'Edinburgh Crowds Alert'


def test_alert_via_email_handles_smtp_exception(caplog):
    with patch('engine.alerting.smtplib.SMTP_SSL') as mock_smtp:
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.send_message.side_effect = SMTPResponseException(550, b'Mock failure')
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Call with defaults
        alert_via_email('Failure test')

        # Check that an error was logged
        assert any('SMTP error' in record.message for record in caplog.records if record.levelname == 'ERROR')
