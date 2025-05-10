from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import DjangoUnicodeDecodeError
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from .forms import PasswordResetRequestForm
from .tokens import password_reset_token
from .models import Users 
from django.template.loader import render_to_string
from .decorators import custom_login_required

@custom_login_required
def account(request):
    user = Users.objects.get(id=request.session['user_id'])  # This automatically fetches the authenticated user from the session
    print(user) 
    return render(request, 'authentication/account.html', {'user': user})

def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            # If the user is authenticated, make sure they only reset their own account
            if request.user.is_authenticated and email != request.user.email:
                messages.error(request, "You can only reset the password for your own account.")
                return redirect("password_reset_request")

            try:
                user = Users.objects.get(email=email)

                # Generate token and UID
                token = password_reset_token.make_token(user)
                uid = urlsafe_base64_encode(str(user.id).encode())

                # Construct reset URL
                current_site = get_current_site(request)
                reset_url = f"{request.scheme}://{current_site.domain}/password-reset/{uid}/{token}/"

                # Send password reset email
                subject = "Password Reset Request"
                message = render_to_string("authentication/password_reset_email.html", {
                    "user": user,
                    "reset_url": reset_url,
                })
                send_mail(subject, message, 'no-reply@example.com', [email])

            except Users.DoesNotExist:
                # Don't reveal whether the email exists
                pass

            messages.success(request, "If that email exists, a password reset link has been sent.")
            return redirect("login")
    else:
        form = PasswordResetRequestForm()

    return render(request, "authentication/password_reset_form.html", {"form": form})



def password_reset_confirm(request, uidb64, token):
    try:
        # Decode the UID (user ID) from the URL and get the user object
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Users.objects.get(id=uid)

        # Check if the token is valid for the user
        if password_reset_token.check_token(user, token):
            if request.method == "POST":
                # Use SetPasswordForm to validate and handle password change
                form = SetPasswordForm(user, request.POST)
                if form.is_valid():
                    form.save()  # Save the new password
                    messages.success(request, "Your password has been reset successfully!")
                    return redirect("login")
                else:
                    # If form is invalid, show errors and retain form state
                    messages.error(request, "There was an error resetting your password. Please try again.")
                    return render(request, "authentication/password_reset_confirm.html", {
                        "form": form,
                        "uidb64": uidb64,
                        "token": token
                    })

            # Render the password reset form when GET request is made
            form = SetPasswordForm(user)
            return render(request, "authentication/password_reset_confirm.html", {
                "form": form,
                "uidb64": uidb64,
                "token": token
            })

        else:
            messages.error(request, "The reset link is invalid or has expired. Please request a new one.")
            return redirect("password_reset_request")

    except (Users.DoesNotExist, ValueError, TypeError, DjangoUnicodeDecodeError):
        # Catch any decoding issues or invalid user errors
        messages.error(request, "The user associated with this reset link does not exist. Please request a new password reset.")
        return redirect("password_reset_request")



def login(request):
    if request.method == "POST":
        username = request.POST.get("username")  # this is the email
        password = request.POST.get("password")

        if not username or not password:
            messages.error(request, "Please enter both email and password")
            return redirect("login")

        try:
            # Fetch user by email
            user = Users.objects.get(email=username)
        except Users.DoesNotExist:
            messages.error(request, "Invalid email or password")
            return redirect("login")

        # Check if the provided password matches the stored hash
        if check_password(password, user.password_hash):
            messages.success(request, f"Welcome, {user.name}!")

            # Store user info in session
            request.session['user_id'] = user.id
            request.session['user_name'] = user.name
            request.session['user_role'] = user.role

            return redirect("dashboard")  # Change if you want to redirect elsewhere
        else:
            messages.error(request, "Invalid email or password")
            return redirect("login")

    return render(request, 'login.html')

#def loginView(request):
#    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()  # Clears all session data

    return redirect('login')
