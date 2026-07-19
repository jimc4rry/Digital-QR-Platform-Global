from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'excerpt', 'meta_description', 'body', 'is_published']
        widgets = {
            'excerpt': forms.Textarea(attrs={'rows': 2}),
            'body': forms.Textarea(attrs={'rows': 18}),
        }
        help_texts = {
            'slug': 'Leave blank to auto-generate from the title.',
        }
