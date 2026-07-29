"""Publishes the next not-yet-published post from blog/content/marketing_posts.py.

Meant to run once a day (see .github/workflows/daily-blog-post.yml). Matches
by title against existing Post rows, so it's safe to re-run - if today's post
already exists (e.g. the workflow ran twice), it just moves on to the next
one instead of duplicating it. Once every post in the list has been
published, it's a no-op until more entries are added to the file."""
from django.core.management.base import BaseCommand

from blog.content.marketing_posts import MARKETING_POSTS
from blog.models import Post


class Command(BaseCommand):
    help = 'Publishes the next unpublished post from the marketing content queue.'

    def handle(self, *args, **options):
        existing_titles = set(Post.objects.values_list('title', flat=True))

        for entry in MARKETING_POSTS:
            if entry['title'] in existing_titles:
                continue

            post = Post.objects.create(
                title=entry['title'],
                excerpt=entry['excerpt'],
                meta_description=entry['meta_description'],
                body=entry['body'],
                is_published=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Published "{post.title}" (slug={post.slug})'))
            return

        self.stdout.write('Nothing to publish - every post in the queue already exists.')
