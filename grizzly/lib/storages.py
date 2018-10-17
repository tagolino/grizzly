import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from storages.backends.gcloud import GoogleCloudStorage


class EmailThread(threading.Thread):
    """
    @brief      Avoids the usual delay on the backend when sending an e-mail
    """
    def __init__(self, subject, body, from_email, recipient_list,
                 fail_silently, html_message):
        self.subject = subject
        self.body = body
        self.recipient_list = recipient_list
        self.from_email = from_email
        self.fail_silently = fail_silently
        self.html_message = html_message
        threading.Thread.__init__(self)

    def run(self):
        msg = EmailMultiAlternatives(self.subject, self.body, self.from_email,
                                     self.recipient_list)
        if self.html_message:
            msg.attach_alternative(self.html_message, "text/html")
        msg.send(self.fail_silently)


class GoogleMediaFilesStorage(GoogleCloudStorage):

    def _save(self, name, content):
        name = f'{settings.MEDIA_URL[1:]}{name}'
        return super()._save(name, content)

    def url(self, name):
        """
        @brief      for implementation of CDN using image field url
        @return     Dynamic return of CDN or local URL
        """
        if settings.CDN_HOSTNAME:
            url = f'{settings.CDN_HOSTNAME}/{name}'
            return url
        return super().url(name)


class GoogleStaticFilesStorage(GoogleCloudStorage):
    def url(self, name):
        name = f'static/{name}'
        return super().url(name)
