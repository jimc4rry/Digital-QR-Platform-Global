from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import Count, Sum, F
from django.db.models.functions import TruncDate
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from accounts.models import User
from .models import Restaurant, Category, Product, ProductOption, StaffMember, PromoCode, LoyaltyAccount, RestaurantTable
from .forms import RestaurantForm, CategoryForm, ProductForm, ProductOptionForm, StaffCreationForm, PromoCodeForm, RestaurantTableForm, LoyaltyAccountForm
from .permissions import restaurant_role_required
import json

# Same escaping django.utils.html.json_script uses internally - required because this
# JSON gets embedded inside a <script> tag, and restaurant/product names or descriptions
# are free text set by the restaurant owner. Without it, a name containing "</script>"
# could break out of the script tag (the browser's HTML parser looks for that literal
# sequence regardless of it being "inside a JSON string").
_JSON_LD_SCRIPT_ESCAPES = {ord('<'): '\\u003C', ord('>'): '\\u003E', ord('&'): '\\u0026'}

DIET_SCHEMA_URLS = {
    'is_vegan': 'https://schema.org/VeganDiet',
    'is_vegetarian': 'https://schema.org/VegetarianDiet',
    'is_gluten_free': 'https://schema.org/GlutenFreeDiet',
}


def _build_menu_json_ld(request, restaurant, categories):
    """Restaurant + Menu structured data (schema.org) for the public menu page, so search
    engines can understand the restaurant's dishes and prices directly, not just the page text."""
    menu_sections = []
    for category in categories:
        items = []
        for product in category.products.all():
            if not product.is_available:
                continue
            item = {
                '@type': 'MenuItem',
                'name': product.get_display_name(),
                'offers': {
                    '@type': 'Offer',
                    'price': str(product.price),
                    'priceCurrency': restaurant.currency,
                },
            }
            if product.description:
                item['description'] = product.description
            diets = [url for field, url in DIET_SCHEMA_URLS.items() if getattr(product, field)]
            if diets:
                item['suitableForDiet'] = diets
            items.append(item)
        if items:
            menu_sections.append({
                '@type': 'MenuSection',
                'name': category.name,
                'hasMenuItem': items,
            })

    data = {
        '@context': 'https://schema.org',
        '@type': 'Restaurant',
        'name': restaurant.name,
        'url': request.build_absolute_uri(),
    }
    if restaurant.description:
        data['description'] = restaurant.description
    if restaurant.address:
        data['address'] = restaurant.address
    if restaurant.phone:
        data['telephone'] = restaurant.phone
    if restaurant.logo:
        data['image'] = request.build_absolute_uri(restaurant.logo.url)
    if menu_sections:
        data['hasMenu'] = {'@type': 'Menu', 'hasMenuSection': menu_sections}

    return json.dumps(data).translate(_JSON_LD_SCRIPT_ESCAPES)


@never_cache
def public_menu(request, token, table_id=None):
    """Public view for customers to see the menu. The restaurant's own QR code (no table_id)
    is view-only - ordering is only possible by scanning a specific table's QR code, which
    pins the order to that table and the customer can't change it.

    never_cache matters more here than almost anywhere else in the app: the page embeds
    a CSRF token directly in inline JS for the order-submission fetch() call. If a CDN or
    browser ever caches this page, every customer who hits that cached copy gets the same
    stale token, and every order they try to place fails CSRF verification silently."""
    restaurant = get_object_or_404(Restaurant, qr_code_token=token, is_active=True)
    categories = restaurant.categories.filter(is_active=True).prefetch_related('products__options')

    table = None
    if table_id is not None:
        table = get_object_or_404(RestaurantTable, pk=table_id, restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'categories': categories,
        'allow_ordering': table is not None and restaurant.allow_ordering and restaurant.user.has_ordering(),
        'table': table,
        'menu_json_ld': _build_menu_json_ld(request, restaurant, categories),
    }
    return render(request, 'restaurants/public_menu.html', context)

@restaurant_role_required('employee')
def dashboard(request):
    """Restaurant dashboard - counts only, safe for any staff role to view"""
    restaurant = request.restaurant

    total_products = Product.objects.filter(category__restaurant=restaurant).count()
    active_products = Product.objects.filter(category__restaurant=restaurant, is_available=True).count()
    total_categories = Category.objects.filter(restaurant=restaurant).count()
    total_orders = restaurant.orders.count()
    recent_orders = restaurant.orders.all()[:10]

    context = {
        'restaurant': restaurant,
        'total_products': total_products,
        'active_products': active_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'recent_orders': recent_orders,
    }
    return render(request, 'restaurants/dashboard.html', context)

@restaurant_role_required('admin')
def restaurant_settings(request):
    restaurant = request.restaurant

    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, _('Settings saved successfully!'))
            return redirect('restaurant_settings')
    else:
        form = RestaurantForm(instance=restaurant)

    context = {
        'form': form,
        'restaurant': restaurant,
    }
    return render(request, 'restaurants/settings.html', context)

@restaurant_role_required('admin')
def category_list(request):
    restaurant = request.restaurant
    categories = Category.objects.filter(restaurant=restaurant).annotate(product_count=Count('products'))

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.restaurant = restaurant
            category.save()
            messages.success(request, _('Category created successfully!'))
            return redirect('category_list')
    else:
        form = CategoryForm()

    context = {
        'categories': categories,
        'form': form,
        'restaurant': restaurant,
    }
    return render(request, 'restaurants/category_list.html', context)

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, restaurant=request.restaurant)
    category.delete()
    messages.success(request, _('Category deleted successfully!'))
    return redirect('category_list')

@restaurant_role_required('employee')
def product_list(request):
    restaurant = request.restaurant
    products = Product.objects.filter(category__restaurant=restaurant).select_related('category')
    can_manage = request.staff_role in ('owner', 'admin')

    form = None
    if can_manage:
        if request.method == 'POST':
            form = ProductForm(request.POST, request.FILES, restaurant=restaurant)
            if form.is_valid():
                product = form.save(commit=False)
                product.save()
                messages.success(request, _('Product created successfully!'))
                return redirect('product_list')
        else:
            form = ProductForm(restaurant=restaurant)
    elif request.method == 'POST':
        return HttpResponseForbidden(_('You do not have permission to add products.'))

    page_obj = Paginator(products, 20).get_page(request.GET.get('page'))

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'form': form,
        'restaurant': restaurant,
        'can_manage': can_manage,
    }
    return render(request, 'restaurants/product_list.html', context)

@restaurant_role_required('admin')
def product_edit(request, pk):
    restaurant = request.restaurant
    product = get_object_or_404(Product, pk=pk, category__restaurant=restaurant)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, restaurant=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, _('Product updated successfully!'))
            return redirect('product_list')
    else:
        form = ProductForm(instance=product, restaurant=restaurant)

    options = ProductOption.objects.filter(product=product)

    context = {
        'form': form,
        'product': product,
        'options': options,
        'restaurant': restaurant,
    }
    return render(request, 'restaurants/product_edit.html', context)

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, category__restaurant=request.restaurant)
    product.delete()
    messages.success(request, _('Product deleted successfully!'))
    return redirect('product_list')

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def product_option_add(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    try:
        product = get_object_or_404(Product, pk=data['product_id'], category__restaurant=request.restaurant)
    except Http404:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except (KeyError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid product_id'}, status=400)

    try:
        option = ProductOption.objects.create(
            product=product,
            name=data['name'],
            price_adjustment=data.get('price_adjustment', 0),
            is_default=data.get('is_default', False)
        )
    except (KeyError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid option data'}, status=400)

    return JsonResponse({
        'success': True,
        'id': option.id,
        'name': option.name,
        'price_adjustment': str(option.price_adjustment),
    })

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def product_option_delete(request, pk):
    option = get_object_or_404(ProductOption, pk=pk, product__category__restaurant=request.restaurant)
    option.delete()
    return JsonResponse({'success': True})

@restaurant_role_required('admin')
def stats_dashboard(request):
    """Sales stats for the Business tier: revenue/orders today/week/month, top products, 14-day trend."""
    from orders.models import Order, OrderItem

    restaurant = request.restaurant

    if not restaurant.user.has_stats_dashboard():
        return render(request, 'restaurants/stats_upgrade.html', {'restaurant': restaurant})

    now = timezone.localtime(timezone.now())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    orders_qs = Order.objects.filter(restaurant=restaurant).exclude(status='cancelled')

    def summarize(since):
        agg = orders_qs.filter(created_at__gte=since).aggregate(revenue=Sum('total'), count=Count('id'))
        return {'revenue': agg['revenue'] or 0, 'count': agg['count'] or 0}

    top_products = (
        OrderItem.objects.filter(order__restaurant=restaurant)
        .exclude(order__status='cancelled')
        .values('name')
        .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(F('price') * F('quantity')))
        .order_by('-total_quantity')[:5]
    )

    trend_start = today_start - timedelta(days=13)
    daily_revenue = (
        orders_qs.filter(created_at__gte=trend_start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('total'))
    )
    trend_map = {row['day']: float(row['revenue'] or 0) for row in daily_revenue}
    trend_labels = []
    trend_values = []
    for i in range(14):
        day = (trend_start + timedelta(days=i)).date()
        trend_labels.append(day.strftime('%d/%m'))
        trend_values.append(trend_map.get(day, 0))

    context = {
        'restaurant': restaurant,
        'stats_today': summarize(today_start),
        'stats_week': summarize(week_start),
        'stats_month': summarize(month_start),
        'top_products': top_products,
        'trend_labels': trend_labels,
        'trend_values': trend_values,
    }
    return render(request, 'restaurants/stats_dashboard.html', context)

@restaurant_role_required('owner')
def staff_list(request):
    """Owner-only: create/remove admin and employee accounts for this restaurant."""
    restaurant = request.restaurant
    if not restaurant.user.has_staff_management():
        return render(request, 'restaurants/feature_upgrade.html', {
            'restaurant': restaurant,
            'feature_icon': 'bi-people',
            'feature_title': _('Staff management is available on the Business plan'),
            'feature_description': _('Upgrade to the Business plan to add admin and employee accounts with separate permissions.'),
        })
    staff_members = StaffMember.objects.filter(restaurant=restaurant).select_related('user')

    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1'],
                )
                StaffMember.objects.create(
                    restaurant=restaurant,
                    user=user,
                    role=form.cleaned_data['role'],
                )
            messages.success(request, _('Staff account created successfully!'))
            return redirect('staff_list')
    else:
        form = StaffCreationForm()

    context = {
        'restaurant': restaurant,
        'staff_members': staff_members,
        'form': form,
    }
    return render(request, 'restaurants/staff_list.html', context)

@restaurant_role_required('owner')
@require_http_methods(["POST"])
def staff_delete(request, pk):
    if not request.restaurant.user.has_staff_management():
        return HttpResponseForbidden(_('Staff management is available on the Business plan.'))
    staff = get_object_or_404(StaffMember, pk=pk, restaurant=request.restaurant)
    user_to_remove = staff.user
    staff.delete()
    user_to_remove.delete()
    messages.success(request, _('Staff account removed.'))
    return redirect('staff_list')

@restaurant_role_required('admin')
def table_list(request):
    restaurant = request.restaurant
    if not restaurant.user.has_ordering():
        return render(request, 'restaurants/feature_upgrade.html', {
            'restaurant': restaurant,
            'feature_icon': 'bi-qr-code',
            'feature_title': _('QR ordering tables are available from the Pro plan'),
            'feature_description': _('Upgrade to the Pro or Business plan to create table QR codes and accept orders.'),
        })
    tables = restaurant.tables.all()

    if request.method == 'POST':
        form = RestaurantTableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.restaurant = restaurant
            try:
                table.save()
                messages.success(request, _('Table added successfully!'))
                return redirect('table_list')
            except IntegrityError:
                form.add_error('number', _('This number already exists for this type.'))
    else:
        form = RestaurantTableForm()

    context = {
        'restaurant': restaurant,
        'tables': tables,
        'form': form,
    }
    return render(request, 'restaurants/table_list.html', context)

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def table_delete(request, pk):
    if not request.restaurant.user.has_ordering():
        return HttpResponseForbidden(_('Tables are available from the Pro plan.'))
    table = get_object_or_404(RestaurantTable, pk=pk, restaurant=request.restaurant)
    table.delete()
    messages.success(request, _('Table deleted.'))
    return redirect('table_list')

@restaurant_role_required('admin')
def promo_code_list(request):
    restaurant = request.restaurant
    if not restaurant.user.has_ordering():
        return render(request, 'restaurants/feature_upgrade.html', {
            'restaurant': restaurant,
            'feature_icon': 'bi-tag',
            'feature_title': _('Promo codes are available from the Pro plan'),
            'feature_description': _('Upgrade to the Pro or Business plan to create promo codes for your customers.'),
        })
    promo_codes = PromoCode.objects.filter(restaurant=restaurant)

    if request.method == 'POST':
        form = PromoCodeForm(request.POST)
        if form.is_valid():
            promo = form.save(commit=False)
            promo.restaurant = restaurant
            try:
                promo.save()
                messages.success(request, _('Promo code created successfully!'))
                return redirect('promo_code_list')
            except IntegrityError:
                form.add_error('code', _('This code already exists.'))
    else:
        form = PromoCodeForm()

    context = {
        'restaurant': restaurant,
        'promo_codes': promo_codes,
        'form': form,
    }
    return render(request, 'restaurants/promo_code_list.html', context)

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def promo_code_delete(request, pk):
    if not request.restaurant.user.has_ordering():
        return HttpResponseForbidden(_('Promo codes are available from the Pro plan.'))
    promo = get_object_or_404(PromoCode, pk=pk, restaurant=request.restaurant)
    promo.delete()
    messages.success(request, _('Promo code deleted.'))
    return redirect('promo_code_list')

@restaurant_role_required('admin')
def loyalty_list(request):
    """Top loyalty customers by points, keyed by phone number."""
    restaurant = request.restaurant
    if not restaurant.user.has_ordering():
        return render(request, 'restaurants/feature_upgrade.html', {
            'restaurant': restaurant,
            'feature_icon': 'bi-star',
            'feature_title': _('Loyalty is available from the Pro plan'),
            'feature_description': _('Upgrade to the Pro or Business plan to give loyalty points to your customers.'),
        })
    accounts = LoyaltyAccount.objects.filter(restaurant=request.restaurant)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        accounts = accounts.filter(phone__icontains=search_query)

    page_obj = Paginator(accounts, 20).get_page(request.GET.get('page'))

    context = {
        'restaurant': request.restaurant,
        'loyalty_accounts': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'restaurants/loyalty_list.html', context)

@restaurant_role_required('admin')
def loyalty_edit(request, pk):
    if not request.restaurant.user.has_ordering():
        return HttpResponseForbidden(_('Loyalty is available from the Pro plan.'))
    account = get_object_or_404(LoyaltyAccount, pk=pk, restaurant=request.restaurant)

    if request.method == 'POST':
        form = LoyaltyAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, _('Loyalty account updated!'))
            return redirect('loyalty_list')
    else:
        form = LoyaltyAccountForm(instance=account)

    context = {
        'restaurant': request.restaurant,
        'form': form,
        'account': account,
    }
    return render(request, 'restaurants/loyalty_edit.html', context)

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def loyalty_delete(request, pk):
    if not request.restaurant.user.has_ordering():
        return HttpResponseForbidden(_('Loyalty is available from the Pro plan.'))
    account = get_object_or_404(LoyaltyAccount, pk=pk, restaurant=request.restaurant)
    account.delete()
    messages.success(request, _('Loyalty account deleted.'))
    return redirect('loyalty_list')
