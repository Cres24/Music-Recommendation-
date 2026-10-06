from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from .models import User


from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Full Name"
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email Address"
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username"
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm Password"
        })
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "password1", "password2"]



class RegisterForm(UserCreationForm):

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
        ]
from django import forms
from .models import MusicPreference


class MusicPreferenceForm(forms.ModelForm):

    GENRE_CHOICES = [
        ("pop", "Pop"),
        ("rock_metal", "Rock / Metal"),
        ("hiphop_rap", "Hip-Hop / Rap"),
        ("rnb_soul", "R&B / Soul"),
        ("electronic_edm", "Electronic / EDM"),
        ("indie_alternative", "Indie / Alternative"),
        ("classical_jazz", "Classical / Jazz"),
        ("country_folk", "Country / Folk"),
        ("kpop_jpop", "K-Pop / J-Pop"),
        ("mixed", "Other / A mix of everything"),
    ]

    PRIORITY_CHOICES = [
        ("melody", "Catchy melody"),
        ("lyrics", "Lyrics / storytelling"),
        ("beat", "Beat / rhythm"),
        ("vocals", "Vocals"),
        ("instrumentals", "Instrumentals"),
        ("vibe", "Overall atmosphere / vibe"),
    ]

    MOOD_CHOICES = [
        ("happy", "Happy / upbeat"),
        ("relaxing", "Relaxing / peaceful"),
        ("sad", "Sad / emotional"),
        ("energetic", "Energetic / hype"),
        ("dark", "Dark / intense"),
        ("romantic", "Romantic"),
        ("nostalgic", "Nostalgic"),
    ]

    CONTEXT_CHOICES = [
        ("study", "While studying / working"),
        ("gaming", "While gaming"),
        ("travel", "While traveling / commuting"),
        ("exercise", "While exercising"),
        ("relaxing", "When relaxing"),
        ("party", "At parties / with friends"),
        ("always", "Pretty much all the time"),
    ]

    PLAYLIST_CHOICES = [
        ("popular", "Songs that are currently popular"),
        ("lyrics", "Songs with great lyrics"),
        ("beat", "Songs with a strong beat"),
        ("vocals", "Songs with beautiful vocals"),
        ("unique", "Songs with a unique/interesting sound"),
        ("mood", "Songs that match a specific mood"),
        ("memory", "Songs that remind me of a memory or experience"),
    ]

    favorite_genre = forms.ChoiceField(
        choices=GENRE_CHOICES,
        widget=forms.RadioSelect
    )

    song_priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        widget=forms.RadioSelect
    )

    preferred_mood = forms.ChoiceField(
        choices=MOOD_CHOICES,
        widget=forms.RadioSelect
    )

    listening_context = forms.ChoiceField(
        choices=CONTEXT_CHOICES,
        widget=forms.RadioSelect
    )

    playlist_preference = forms.ChoiceField(
        choices=PLAYLIST_CHOICES,
        widget=forms.RadioSelect
    )

    class Meta:
        model = MusicPreference

        fields = [
            "favorite_genre",
            "song_priority",
            "preferred_mood",
            "listening_context",
            "playlist_preference",
        ]