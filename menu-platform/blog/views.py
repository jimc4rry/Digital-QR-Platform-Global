from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext as _
from accounts.views import platform_admin_required
from .forms import PostForm
from .models import Post


def blog_list(request):
    posts = Post.objects.filter(is_published=True)
    return render(request, 'blog/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, 'blog/blog_detail.html', {'post': post})


@platform_admin_required
def blog_admin_list(request):
    """In-app blog management, styled like the rest of the dashboard - an
    alternative to the raw Django admin for day-to-day post writing."""
    posts = Post.objects.all()
    return render(request, 'blog/admin_list.html', {'posts': posts})


@platform_admin_required
def blog_admin_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Post created.'))
            return redirect('blog:admin_list')
    else:
        form = PostForm()
    return render(request, 'blog/admin_form.html', {'form': form, 'is_new': True})


@platform_admin_required
def blog_admin_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, _('Post updated.'))
            return redirect('blog:admin_list')
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/admin_form.html', {'form': form, 'post': post, 'is_new': False})


@platform_admin_required
def blog_admin_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        post.delete()
        messages.success(request, _('Post deleted.'))
        return redirect('blog:admin_list')
    return render(request, 'blog/admin_delete_confirm.html', {'post': post})
