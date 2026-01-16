from django import forms
from .models import Item, Order, Payment

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'description', 'price', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class ItemSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search for items...', 'class': 'form-control'})
    )
    category = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': 'Min Price', 'class': 'form-control'})
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': 'Max Price', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        from .models import Category
        super(ItemSearchForm, self).__init__(*args, **kwargs)
        
        # Get categories for the dropdown
        categories = Category.objects.all()
        category_choices = [('', 'All Categories')]
        category_choices.extend([(str(c.id), c.name) for c in categories])
        self.fields['category'].choices = category_choices

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_address']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class PaymentForm(forms.ModelForm):
    MONTH_CHOICES = [(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)]
    YEAR_CHOICES = [(str(i), str(i)) for i in range(2023, 2033)]
    
    card_number = forms.CharField(
        max_length=16,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Card Number', 
            'autocomplete': 'off',
            'class': 'form-control',
            'data-mask': '0000 0000 0000 0000'
        })
    )
    card_expiry_month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    card_expiry_year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    card_cvv = forms.CharField(
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'CVV',
            'autocomplete': 'off',
            'class': 'form-control',
            'data-mask': '000'
        })
    )
    
    class Meta:
        model = Payment
        fields = ['payment_method']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number')
        # Remove spaces or any other separators
        card_number = ''.join(card_number.split())
        
        # Basic validation
        if not card_number.isdigit():
            raise forms.ValidationError("Card number should contain only digits.")
        if len(card_number) < 13 or len(card_number) > 19:
            raise forms.ValidationError("Card number should be between 13 and 19 digits.")
        
        # For demo purposes, accept any card number that passes basic validation
        return card_number
    
    def clean_card_cvv(self):
        cvv = self.cleaned_data.get('card_cvv')
        
        # Basic validation
        if not cvv.isdigit():
            raise forms.ValidationError("CVV should contain only digits.")
        if not (3 <= len(cvv) <= 4):
            raise forms.ValidationError("CVV should be 3 or 4 digits.")
        
        return cvv