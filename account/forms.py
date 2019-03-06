from django import forms

from captcha.fields import CaptchaField


class CaptchaForm(forms.Form):
    """
    @brief      request and validate captcha
    """

    verification_code = CaptchaField()
