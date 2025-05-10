from django.contrib.auth.tokens import PasswordResetTokenGenerator

class UserPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

password_reset_token = UserPasswordResetTokenGenerator()
