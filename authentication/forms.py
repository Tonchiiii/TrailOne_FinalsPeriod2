from django import forms

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email Address", max_length=254)
    
    # Example of adding a custom field (e.g., reCAPTCHA for security)
    # reCAPTCHAField = forms.CharField(label="reCAPTCHA")
