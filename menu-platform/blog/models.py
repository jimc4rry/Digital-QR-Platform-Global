from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.CharField(
        max_length=300, blank=True,
        help_text="Short summary shown on the blog list page. Also used as the meta description if that field is left blank.",
    )
    meta_description = models.CharField(
        max_length=160, blank=True,
        help_text="Defaults to the excerpt if left blank.",
    )
    body = models.TextField(help_text="HTML is rendered as-is.")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_meta_description(self):
        return self.meta_description or self.excerpt

    def get_absolute_url(self):
        return reverse('blog:blog_detail', kwargs={'slug': self.slug})
