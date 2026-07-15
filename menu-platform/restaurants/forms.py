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
            'name': _('Όνομα Εστιατορίου'),
            'description': _('Περιγραφή'),
            'address': _('Διεύθυνση'),
            'phone': _('Τηλέφωνο'),
            'email': 'Email',
            'logo': _('Λογότυπο'),
            'cover_image': _('Εξώφυλλο'),
            'allow_ordering': _('Να δέχεται παραγγελίες'),
            'loyalty_enabled': _('Ενεργοποίηση Loyalty (πόντοι για πελάτες)'),
            'tax_rate': _('ΦΠΑ (%)'),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'order', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'name': _('Όνομα Κατηγορίας'),
            'description': _('Περιγραφή'),
            'order': _('Σειρά Εμφάνισης'),
            'is_active': _('Ενεργό'),
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
            'category': _('Κατηγορία'),
            'name': _('Όνομα Προϊόντος (Ελληνικά)'),
            'name_en': _('Όνομα Προϊόντος (Αγγλικά)'),
            'description': _('Περιγραφή'),
            'price': _('Τιμή (€)'),
            'old_price': _('Παλιά Τιμή (€)'),
            'image': _('Φωτογραφία'),
            'is_available': _('Διαθέσιμο'),
            'is_featured': _('Προτεινόμενο'),
            'is_vegan': 'Vegan',
            'is_vegetarian': 'Vegetarian',
            'is_gluten_free': _('Χωρίς Γλουτένη'),
            'is_spicy': _('Πικάντικο'),
            'order': _('Σειρά Εμφάνισης'),
            'preparation_time': _('Χρόνος Παρασκευής (λεπτά)'),
        }

class ProductOptionForm(forms.ModelForm):
    class Meta:
        model = ProductOption
        fields = ['name', 'price_adjustment', 'is_default']
        widgets = {
            'price_adjustment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'name': _('Όνομα Επιλογής'),
            'price_adjustment': _('Προσαρμογή Τιμής (€)'),
            'is_default': _('Προεπιλεγμένο'),
        }


class StaffCreationForm(forms.Form):
    username = forms.CharField(max_length=150, label=_('Όνομα Χρήστη'))
    password1 = forms.CharField(widget=forms.PasswordInput, label=_('Κωδικός'))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_('Επιβεβαίωση Κωδικού'))
    role = forms.ChoiceField(choices=StaffMember.ROLE_CHOICES, label=_('Ρόλος'))

    def clean_username(self):
        from accounts.models import User
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_('Αυτό το όνομα χρήστη υπάρχει ήδη.'))
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
            raise forms.ValidationError(_('Οι κωδικοί δεν ταιριάζουν.'))
        return cleaned


class RestaurantTableForm(forms.ModelForm):
    class Meta:
        model = RestaurantTable
        fields = ['table_type', 'number']
        labels = {
            'table_type': _('Τύπος'),
            'number': _('Αριθμός / Όνομα'),
        }


class LoyaltyAccountForm(forms.ModelForm):
    class Meta:
        model = LoyaltyAccount
        fields = ['phone', 'points']
        labels = {
            'phone': _('Τηλέφωνο'),
            'points': _('Πόντοι'),
        }


class PromoCodeForm(forms.ModelForm):
    class Meta:
        model = PromoCode
        fields = ['code', 'discount_percent', 'valid_until', 'max_uses', 'is_active']
        widgets = {
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'code': _('Κωδικός Έκπτωσης'),
            'discount_percent': _('Έκπτωση (%)'),
            'valid_until': _('Ισχύει έως (προαιρετικό)'),
            'max_uses': _('Μέγιστες χρήσεις (προαιρετικό)'),
            'is_active': _('Ενεργός'),
        }
