from django import forms
from .models import UserProfile, Album, Media

class UserRegisterForm(forms.Form):
    """Registration form for new users."""
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data

class UserLoginForm(forms.Form):
    """Login form for existing users."""
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'})
        }

class CombinedProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['email', 'bio', 'profile_picture']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'})
        }

class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class MediaForm(forms.ModelForm):
    album = forms.ModelChoiceField(
        queryset=Album.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Media
        fields = ['title', 'description', 'file', 'album', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
        
        if user_id:
            self.fields['album'].queryset = Album.objects.filter(user_id=user_id)
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size - limit to 100MB
            if file.size > 100 * 1024 * 1024:  # 100MB in bytes
                raise forms.ValidationError("File size must not exceed 100MB.")
        return file

    add_to_favorites = forms.BooleanField(
        required=False,
        initial=False,
        label='Add to Favorites',
        help_text='Check this box to add this media to your favorites immediately'
    )