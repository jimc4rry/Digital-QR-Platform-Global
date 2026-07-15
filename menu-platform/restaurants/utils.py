from django.core.exceptions import ValidationError
from django.utils.text import slugify

MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_image_file_size(file):
    if file.size > MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError(f'The file must not exceed {MAX_IMAGE_UPLOAD_SIZE // (1024 * 1024)}MB.')


def generate_unique_slug(instance, source_text, queryset):
    """Slugify source_text and, if it collides within queryset, append -2, -3, ... until unique."""
    base_slug = slugify(source_text) or 'item'
    slug = base_slug
    counter = 2
    while queryset.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug
