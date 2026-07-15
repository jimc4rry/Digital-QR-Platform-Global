from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from .models import Restaurant, Category, Product, ProductOption, StaffMember, PromoCode, RestaurantTable, LoyaltyAccount

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'description', 'address', 'phone', 'email', 'logo', 'cover_image',
                  'allow_ordering', 'loyalty_enabled', 'tax_rate']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'name': _('Restaurant Name'),
            'description': _('Description'),
            'address': _('Address'),
            'phone': _('Phone'),
            'email': 'Email',
            'logo': _('Logo'),
            'cover_image': _('Cover Image'),
            'allow_ordering': _('Accept orders'),
            'loyalty_enabled': _('Enable Loyalty (points for customers)'),
            'tax_rate': _('Tax (%)'),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'order', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'name': _('Category Name'),
            'description': _('Description'),
            'order': _('Display Order'),
            'is_active': _('Active'),
        }

class ProductForm(forms.ModelForm):
    def __init__(self, *args, restaurant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if restaurant is not None:
            self.fields['category'].queryset = Category.objects.filter(restaurant=restaurant)
        elif self.instance and self.instance.pk:
            self.fields['category'].queryset = Category.objects.filter(restaurant=self.instance.category.restaurant)

    class Meta:
        model = Product
        fields = ['category', 'name', 'name_en', 'description', 'price', 'old_price', 'image',
                  'is_available', 'is_featured', 'is_vegan', 'is_vegetarian',
                  'is_gluten_free', 'is_spicy', 'order', 'preparation_time']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'old_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'category': _('Category'),
            'name': _('Product Name'),
            'name_en': _('Product Name (English)'),
            'description': _('Description'),
            'price': _('Price'),
            'old_price': _('Old Price'),
            'image': _('Photo'),
            'is_available': _('Available'),
            'is_featured': _('Featured'),
            'is_vegan': 'Vegan',
            'is_vegetarian': 'Vegetarian',
            'is_gluten_free': _('Gluten-Free'),
            'is_spicy': _('Spicy'),
            'order': _('Display Order'),
            'preparation_time': _('Preparation Time (minutes)'),
        }

class ProductOptionForm(forms.ModelForm):
    class Meta:
        model = ProductOption
        fields = ['name', 'price_adjustment', 'is_default']
        widgets = {
            'price_adjustment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'name': _('Option Name'),
            'price_adjustment': _('Price Adjustment'),
            'is_default': _('Default'),
        }


class StaffCreationForm(forms.Form):
    username = forms.CharField(max_length=150, label=_('Username'))
    password1 = forms.CharField(widget=forms.PasswordInput, label=_('Password'))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_('Confirm Password'))
    role = forms.ChoiceField(choices=StaffMember.ROLE_CHOICES, label=_('Role'))

    def clean_username(self):
        from accounts.models import User
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_('This username already exists.'))
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned


class RestaurantTableForm(forms.ModelForm):
    class Meta:
        model = RestaurantTable
        fields = ['table_type', 'number']
        labels = {
            'table_type': _('Type'),
            'number': _('Number / Name'),
        }


class LoyaltyAccountForm(forms.ModelForm):
    class Meta:
        model = LoyaltyAccount
        fields = ['phone', 'points']
        labels = {
            'phone': _('Phone'),
            'points': _('Points'),
        }


class PromoCodeForm(forms.ModelForm):
    class Meta:
        model = PromoCode
        fields = ['code', 'discount_percent', 'valid_until', 'max_uses', 'is_active']
        widgets = {
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'code': _('Promo Code'),
            'discount_percent': _('Discount (%)'),
            'valid_until': _('Valid Until (optional)'),
            'max_uses': _('Max Uses (optional)'),
            'is_active': _('Active'),
        }
