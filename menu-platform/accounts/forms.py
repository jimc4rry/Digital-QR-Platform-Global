from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from .models import User, BUSINESS_TYPE_CHOICES


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = _('Current Password')
        self.fields['new_password1'].label = _('New Password')
        self.fields['new_password2'].label = _('Confirm New Password')

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    business_name = forms.CharField(max_length=200, required=True, label=_('Business Name'))
    phone = forms.CharField(max_length=20, required=False, label=_('Phone'))
    tax_id = forms.CharField(
        max_length=32, required=False, label=_('VAT / Tax ID'),
        help_text=_('Optional - if your business has one.'),
    )
    business_type = forms.ChoiceField(
        choices=BUSINESS_TYPE_CHOICES,
        label=_('Business Type')
    )
    # Honeypot: invisible to real users (off-screen, out of tab order, not read by
    # screen readers), so only a bot that blindly fills every input will populate it.
    # Left blank by humans - checked in the signup view, never saved to the User model.
    website = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
            'aria-hidden': 'true',
            'style': 'position:absolute; left:-9999px; width:1px; height:1px;',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'business_name', 'business_type', 'tax_id', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = _('Username')
        self.fields['password1'].label = _('Password')
        self.fields['password2'].label = _('Confirm Password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.business_name = self.cleaned_data['business_name']
        user.business_type = self.cleaned_data['business_type']
        user.tax_id = self.cleaned_data['tax_id']
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user


PLAN_ORDER = ['basic', 'pro', 'business']


def get_upgradable_plans(current_plan):
    """Plans strictly above current_plan - never the same tier, never a downgrade."""
    current_index = PLAN_ORDER.index(current_plan) if current_plan in PLAN_ORDER else 0
    return [p for p in PLAN_ORDER[current_index + 1:] if p != 'basic']


def get_purchasable_plans(current_plan, subscription_active):
    """Plans checkout should offer right now: strictly-above upgrades, plus the
    user's own current tier if they've never actually paid for it yet (e.g.
    straight after signup, before their first Paddle checkout)."""
    upgradable = get_upgradable_plans(current_plan)
    if not subscription_active and current_plan in PLAN_ORDER and current_plan not in upgradable:
        return [current_plan] + upgradable
    return upgradable


class PlatformSubscriptionForm(forms.ModelForm):
    """Used by the platform admin panel to manually manage a business's subscription -
    for support/override cases outside the normal Paddle checkout flow."""
    class Meta:
        model = User
        fields = ['subscription_plan', 'subscription_active', 'subscription_ends']
        widgets = {
            'subscription_ends': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'subscription_plan': _('Subscription Plan'),
            'subscription_active': _('Subscription Active'),
            'subscription_ends': _('Subscription Ends (optional)'),
        }
