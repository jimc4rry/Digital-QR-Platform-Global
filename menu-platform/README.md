# GetMenuHub — Restaurant Growth Platform (Digital Menu, Ordering, Loyalty & Staff Tools)

Django SaaS platform ([getmenuhub.com](https://getmenuhub.com)) built around
a QR code: a digital menu, optional table/sunbed ordering (zero commission),
a phone-number loyalty program, promo codes, role-based staff accounts, sales
statistics, and real subscription billing via **Paddle** (Merchant of
Record — handles international VAT/sales tax automatically). See
[`PRODUCT_SHOWCASE.md`](../PRODUCT_SHOWCASE.md) at the repo root for a
screenshot-driven walkthrough of the product and its market positioning;
this file is the engineering reference. Includes a separate mobile app
(Flutter) for owners/staff, and a marketing/SEO site (guides, blog, free
tools, dedicated `/features/*` pages, per-restaurant subdomains) built to
attract organic signups.

Available to businesses worldwide, billed in USD through Paddle. The
dashboard/marketing site is available in **English, Greek, Spanish and
French** (see §5.6) — English is always the source language and the only
one anonymous/bot traffic ever sees, so SEO stays stable regardless of a
visitor's browser language.

---

## 1. What the app does

A business owner signs up (with a **30-day free trial** on the Basic plan),
builds their menu (categories + products), and the platform automatically
generates a unique **QR code**. The customer scans the QR code at their table
or sunbed, sees the menu in their phone's browser (no app install), and — if
the restaurant has ordering enabled — can add products to a cart and send an
order directly from there.

The business manages everything from a dashboard (web) or the mobile app:
menu, orders, tables/sunbeds, staff, discount codes, customer loyalty, sales
statistics, and their subscription. Staff can also build and submit an order
themselves (`/orders/new/`) — same product picker and server-side pricing as
the public menu, for phone orders or walk-ins — and the full menu can be
exported as a branded, print-ready PDF at any time (`menu_pdf.py`).

The authenticated dashboard nav is deliberately **separate from the public
marketing nav** the moment someone is logged in — grouped into Dashboard /
Menu / Orders / Growth (Loyalty + Promo Codes) / Statistics / Staff, instead
of mixing app links with marketing links (Guides, Blog, free tools) in one
flat bar (`templates/base.html`). A brand-new signup also sees a short
onboarding checklist on the Dashboard (create a category → add a product →
add a table → preview the menu) that disappears automatically once done
(`restaurants/views.py::dashboard`).

## 2. User Flow

### A. Restaurant Owner
1. **Sign up** (`/accounts/signup/`) — creates a user account. A `Restaurant`
   is created **automatically** at the same time (1-to-1 `User` ↔
   `Restaurant` relationship), with a random `qr_code_token` and a QR code
   image generated on the model's first `save()`. The account starts with a
   **30-day free trial** on the Basic plan (`subscription_active=True`,
   `subscription_ends=+30d`). Two emails fire in the background: a welcome
   email to the new owner, and an internal alert to `info@getmenuhub.com`
   with the new business's name/type/username/email/phone
   (`accounts/views.py::signup`) - see §5.5 for why this can't block the
   request.
2. **Creates Categories** (e.g. "Starters", "Mains" — reorderable with a
   click; a category deleted later re-homes its products to an auto-created
   "Other" category instead of destroying them) and **Products** (price,
   photo, dietary labels: vegan/vegetarian/gluten-free/spicy, optional
   per-product "options" like size/filling with a price adjustment, either
   mutually-exclusive radio groups or independent add-on checkboxes). The
   Products page supports search, category filtering, and **bulk actions**
   (select multiple → mark available/unavailable, move to another category,
   or delete) for restaurants running 40+ items
   (`restaurants/views.py::product_bulk_action`).
3. **Enables ordering** (`allow_ordering`) from Settings, if their
   subscription plan allows it (see §4), and creates **Tables or Sunbeds**
   (`/restaurant/tables/`) — each gets its own QR code; the same number can
   exist as both a table *and* a sunbed at once without conflict (unique per
   type, not global).
4. **Prints/shares the QR code** — the general one leads to
   `https://<domain>/menu/<qr_code_token>/`, the per-table/sunbed one to
   `.../menu/<qr_code_token>/table/<id>/` (the table/sunbed is already
   preselected on the order).
5. Optionally: **invites staff** (Admin/Employee — see §3), creates
   **discount codes**, tracks **customer loyalty** and **sales statistics**.
6. When the trial (or a paid period) ends, the dashboard **locks
   automatically** until a plan is chosen/paid via Paddle (see §4) — no cron
   job needed, the check runs live on every request.

### B. Customer (anonymous, no account)
1. Scans the QR code → `public_menu` view → sees the menu (categories/products),
   with "Table X" or "Sunbed X" shown if the QR was for a specific spot.
2. If the restaurant accepts orders: adds products to a cart (client-side JS,
   no reload), optionally enters a name/discount code (table/sunbed are
   already pre-filled from the QR).
3. Sends the order → `POST /orders/api/create/<token>/`. **Prices are always
   recalculated server-side** from the database (client-sent prices are never
   trusted) — this prevents price tampering. The table/sunbed type and number
   are also verified server-side to actually exist for the restaurant. If a
   discount code is given, its validity is checked
   (`PromoCode.is_valid_now()`) and the discount applied to the subtotal
   before tax. If a phone number is given, the customer earns **1 loyalty
   point per currency unit** spent (cumulative, per phone+restaurant).
4. The owner/staff are notified **immediately by email** (`notify_new_order`)
   and by **push notification** on the mobile app (if Firebase is
   configured), and see a badge with the pending order count in the navbar
   (polled every 20s).

### C. Staff manage an order (web or mobile app)
1. View the order list (`/orders/` or in the mobile app) and open one.
2. Change its status (Pending → Confirmed → Preparing → Ready →
   Delivered/Cancelled).
3. Every change is logged in `OrderStatusLog` (who, when, from which status to
   which) — visible on the order page as an "Activity Log", so the owner can
   see every staff member's actions.
4. Staff (employee/admin/owner) can also **create an order themselves**
   (`/orders/new/`, `orders/views.py::staff_create_order`) — for a phone
   order or a walk-in, or when a customer would rather just ask. It reuses
   the exact same product picker, option groups, and server-side pricing
   engine as the public menu (`_populate_order_items_and_totals`, shared by
   both `create_order_api` and `staff_create_order_api`), except the table is
   optional (blank = takeaway/phone order) and there's no rate limit, since
   the caller is authenticated staff rather than an anonymous scan.

## 3. Roles & Permissions

Every account is linked to **exactly one** restaurant, either as owner or
staff (`StaffMember` model). The user → restaurant + role mapping is done by
`restaurants/permissions.py::get_restaurant_and_role()`, and enforced on every
view via the `@restaurant_role_required(min_role)` decorator — the same
decorator also checks that the restaurant's subscription is active (see §4),
so no page needed a separate paywall check.

| Role | Dashboard | Categories | Products | Tables/Sunbeds | Orders | Stats/Reports | Codes/Loyalty | Settings | Staff |
|---|---|---|---|---|---|---|---|---|---|
| **Owner** | ✅ | ✅ CRUD | ✅ CRUD | ✅ CRUD | ✅ view+manage | ✅ | ✅ CRUD | ✅ | ✅ CRUD |
| **Admin** | ✅ | ✅ CRUD | ✅ CRUD | ✅ CRUD | ✅ view+manage | ✅ | ✅ CRUD | ✅ | ❌ |
| **Employee** | ✅ (counts only) | ❌ | 👁️ view only | ❌ | ✅ view+manage | ❌ | ❌ | ❌ | ❌ |

The owner creates Admin/Employee accounts from the **Staff** page
(`/restaurant/staff/` or the mobile app) by giving a username+password
directly (no self-signup for staff). A `restaurant_context` context processor
exposes template flags like `can_manage_menu`, `can_view_stats`,
`can_manage_staff` so the navbar adapts automatically per role — the same
pattern exists on the mobile app via `GET /api/v1/me/`.

## 4. Subscription Plans & Billing (Paddle)

The `User.subscription_plan` field controls what the restaurant can do
(always checked via the **owner**, `restaurant.user`, regardless of who's
currently logged in):

| Plan | Price | Unlocks |
|---|---|---|
| **Basic** | $7/month | Menu, categories, products, automatic QR code |
| **Pro** | $19/month | + Online ordering from table/sunbed QR codes, loyalty points, discount codes, email/push notifications, 0% commission |
| **Business** | $39/month | + Sales statistics (dashboard + trend chart + top products), CSV export, staff management |

### 4.1 How billing works

- **Sign up** → 30-day free trial on Basic, no card required.
- **Checkout** (`/accounts/checkout/`) → the owner picks a plan and pays
  through **Paddle's embedded Checkout overlay** (Paddle.js) — card details
  never touch our servers. Paddle acts as Merchant of Record, so it also
  handles VAT/sales tax for the customer's country automatically.
- **Webhook** (`POST /accounts/webhooks/paddle/`, CSRF-exempt, verifies the
  `Paddle-Signature` header against `PADDLE_WEBHOOK_SECRET`) is the **source
  of truth**: handles `subscription.created/updated/activated`,
  `subscription.canceled`, `transaction.completed`,
  `transaction.payment_failed` — syncs plan/status
  (`billing.sync_subscription`) and logs every payment to `Payment`
  (`billing.record_payment_from_transaction`). The same logic also runs
  synchronously right after checkout completes (`payment_success` view) for
  an immediate UI update, without depending on the webhook having arrived yet.
- **Billing management** (`/accounts/billing-portal/`) → redirects to
  Paddle's own customer-portal link (fetched live from the subscription's
  `management_urls`) for updating a card or canceling.
- **Payment history** (`/accounts/payments/`) → `Payment` model, one row per
  Paddle transaction.
- **Subscription-expiry lockout**: `User.has_active_subscription()` checks
  `subscription_active` **and** that `subscription_ends` hasn't passed, live
  on every request — no cron job needed. Built into
  `restaurant_role_required` (web) and `HasRestaurantRole` (mobile API DRF
  permission), so it automatically covers every protected page in both apps.
  An owner with an expired subscription is redirected to checkout; staff
  under an expired owner get a 403 asking them to contact the owner.
- **Setup**: `python manage.py sync_paddle_plans` creates (or finds, if they
  already exist) the Paddle Products/Prices for the three plans and prints
  the price IDs for `.env` (`PADDLE_PRICE_BASIC/PRO/BUSINESS`). Safe to
  re-run — it looks up existing prices by a custom lookup key first.

> Scope note: the lockout only applies to the **staff dashboard** (web +
> mobile). The public menu/customer ordering doesn't lock if the owner's
> subscription expires — intentional, so active customer orders don't
> suddenly stop mid-renewal.

## 5. Architecture

### 5.1 Django apps

```
menu_platform/   # project config: settings, root urls, wsgi/asgi, middleware.py (language +
                 # per-restaurant subdomain routing), seo_views (robots.txt/sitemap.xml),
                 # tool_views (free QR generator, live examples), views (homepage)
accounts/        # custom User model, signup/login/password-change, Paddle billing (billing.py,
                 # checkout/webhook/portal views), Payment model, management command sync_paddle_plans
restaurants/     # Restaurant, Category, Product, ProductOption, StaffMember, RestaurantTable
                 # (table/sunbed), PromoCode, LoyaltyAccount + all owner/admin/employee views
orders/          # Order, OrderItem, OrderStatusLog + public ordering API + reports
api/             # REST API (DRF + JWT) for the Flutter staff app - /api/v1/..., same DB/models
blog/            # DB-backed Post model + public list/detail views + an in-app admin UI
                 # (/blog/manage/...) for writing posts without touching Django admin
feedback/        # floating in-app feedback widget (bug reports/suggestions) + an admin
                 # management UI - deliberately hidden from platform-admin/superuser accounts
templates/       # all HTML templates (split per app + shared base.html), plus the marketing
                 # site: home.html, guides/, blog/, tools/ (free QR generator, printing cost
                 # calculator, staff efficiency calculator), solutions/ (staffing-shortage
                 # landing page)
locale/          # gettext .po/.mo translations for en/el/es/fr (see §5.6)
static/          # static assets (design-system.css holds the shared --mh-* CSS tokens/dark mode)
media/           # uploads (photos, QR codes) - local in dev, S3-compatible in production
```

### 5.1.1 Mobile app (owner/staff, Flutter)

In `mobile_app/` (sibling directory, outside `menu-platform/`) there's a
Flutter app (`menuhub_staff`) for owner/admin/employee — same database, talks
to the `api/` app above via JWT auth. Modern Material 3 theme (light/dark,
follows the system).

Screens:
- **Login** — JWT auth, automatic token refresh.
- **Orders** — list with status filters, detail view with status changes and
  activity log, table/sunbed indicator.
- **Products** — list with on/off availability toggle (admin/owner only;
  employee sees a read-only badge, same permission as the web).
- **Management** (owner/admin only, icon visible based on role) →
  - **Stats**: revenue/orders today-week-month, top products, 14-day trend chart.
  - **Staff** (owner only): list/create/delete admin & employee accounts.
  - **Restaurant Settings**: contact info, tax rate, allow_ordering, loyalty on/off.
  - **Loyalty & Promo Codes**: search/edit customer points, create/delete discount codes.

The exact same role permissions **and** the same expired-subscription lockout
apply as on the web dashboard (they share the same `restaurants/permissions.py`
helpers through the `api/` app). Push notifications (Firebase) are ready
server-side (`api/push.py`) but inactive until a real Firebase project is
added — see `mobile_app/README.md`.

### 5.2 Data model (multi-tenant)

All data hangs off `Restaurant` — that's the tenant boundary. Every view that
touches a restaurant's data always goes through `request.restaurant` (set by
the permission decorator), never a raw `pk` from the URL without scoping to
the right restaurant — this prevents IDOR (one user seeing/changing another
restaurant's data).

```
User (accounts) ──1:1──> Restaurant ──1:N──> Category ──1:N──> Product ──1:N──> ProductOption
     │                        │                                    │
     ├──1:N──> Payment        ├──1:N──> StaffMember (role: admin/employee, own User)
     │  (Paddle txn log)      ├──1:N──> RestaurantTable (table_type: table/sunbed)
     │                        ├──1:N──> PromoCode
     │                        ├──1:N──> LoyaltyAccount (keyed by phone, not a customer account)
     │                        └──1:N──> Order ──1:N──> OrderItem
     │                                      └──1:N──> OrderStatusLog
     └── paddle_customer_id / paddle_subscription_id (Paddle link)
```

Customers **don't have accounts** — orders/loyalty are identified only via
`customer_phone` (a free-text field, not an FK), intentionally, to keep the
scan-and-order experience frictionless. `Order.table_number`/`table_type` is
also a **snapshot** at order time (not an FK to `RestaurantTable`) — if a
table is later renamed or deleted, past orders don't change.

### 5.3 Permission system

- `restaurants/permissions.py` — `get_restaurant_and_role(user)` returns
  `(restaurant, role)`. The `restaurant_role_required(min_role)` decorator
  does `login_required` + 403 if the role is below the required one
  (`employee < admin < owner`) + redirect to checkout (owner) or 403 (staff)
  if the subscription has expired + sets
  `request.restaurant`/`request.staff_role`.
- `api/permissions.py` — `HasRestaurantRole`/`IsRestaurantAdmin`/`IsRestaurantOwner`,
  the DRF equivalent for the mobile app, same role + subscription check.
- `restaurants/context_processors.py` — exposes the same data to **every**
  template (`active_restaurant`, `staff_role`, `can_manage_menu`,
  `can_view_stats`, `can_manage_staff`, `restaurant_accepts_orders`) so the
  navbar doesn't need each view to pass them separately.

### 5.4 Public ordering API (`orders/views.py`)

The most sensitive code in the app, since it's the only anonymous/
unauthenticated endpoint that writes data:

- **Server-side pricing**: each item's price is computed from `Product.price`
  + `ProductOption.price_adjustment` from the database — whatever price the
  client sends is ignored.
- **Tenant scoping**: every `product_id` is verified to belong to the
  restaurant the scanned token points to (`category__restaurant=restaurant`),
  otherwise the order is rejected.
- **Table/sunbed validation**: the number+type combination is verified to
  actually exist (`RestaurantTable.objects.filter(restaurant=..., number=..., table_type=...)`),
  otherwise 403.
- **Rate limiting**: 10 orders / 5 minutes per (IP, restaurant) via Django's
  cache, since `qr_code_token` isn't a secret (it's in the QR code's URL).
- **Validation**: field lengths are truncated to the model's max, quantity
  1-100, any database error (`DatabaseError`) is caught and returns 400
  instead of 500.
- **Transaction**: the whole order+items+promo+loyalty creation happens
  inside `transaction.atomic()` — if anything fails partway, no "orphan" row
  is left behind.

### 5.5 Configuration-driven infrastructure (production-ready without a rewrite)

| Need | How it's solved now (dev) | How it changes in production |
|---|---|---|
| Database | SQLite (default) | Env var `DATABASE_URL=postgres://...` (via `dj-database-url`) |
| File storage | Local filesystem | Env vars `AWS_STORAGE_BUCKET_NAME` + credentials → S3-compatible (AWS S3/Cloudflare R2/Spaces) via `django-storages` |
| Email | Console backend (prints to terminal) by default | Env vars `EMAIL_BACKEND`/`EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` → real SMTP (production uses Brevo). `EMAIL_TIMEOUT` (default 10s) bounds a hung/unreachable SMTP server so it can't block a gunicorn worker; every account email (welcome, password-changed, admin new-signup alert - see §2.A) is sent from a background thread for the same reason - a slow or down SMTP provider degrades to "email silently not sent, logged" rather than a failed/502 request |
| Payments | Paddle **sandbox** (`PADDLE_ENV=sandbox`) | Same code, just live keys (`PADDLE_ENV=production`) + a real webhook endpoint registered in the Paddle dashboard |
| Static files | WhiteNoise | Already production-ready |
| Cookie/HSTS security | Off under `DEBUG=True` | Turned on automatically when `DEBUG=False` |

None of these changes need a code change - only environment variables.

### 5.6 Internationalization (i18n)

The whole public site and dashboard support **English, Greek, Spanish and
French** (`LANGUAGES` in settings) via Django's standard `gettext` machinery
(`{% trans %}`/`{% blocktrans %}`, `.po`/`.mo` catalogs under `locale/<lang>/LC_MESSAGES/`).
A language dropdown (globe icon in the navbar) is available to **every**
visitor, logged in or not.

Two things are deliberately custom rather than using Django's stock
`LocaleMiddleware`, both for SEO safety:

- **`menu_platform.middleware.LanguageMiddleware`** replaces it. Language is
  decided *only* from the `django_language` cookie (set via
  `django.views.i18n.set_language`, which in Django 4.2 stores it as a
  cookie, not in the session) - it deliberately does **not** look at the
  browser's `Accept-Language` header. That means Google (and any other
  cookie-less/anonymous visitor) always gets the canonical English version
  regardless of their locale, so there's exactly one indexable version of
  each page rather than the crawler seeing whatever language its request
  headers happen to imply.
- **`RestaurantSubdomainMiddleware`** runs after `LanguageMiddleware` in
  `MIDDLEWARE` (order matters - a subdomain request can short-circuit before
  reaching the view, so language must already be activated by then) - see
  §5.8.

Schema.org JSON-LD structured data (see §5.7) is always emitted in English,
on purpose - it's for search engines, which are treated as anonymous/English
by the same middleware anyway.

### 5.7 SEO

Dynamic meta tags (title/description/OG/canonical) via template blocks in
`base.html`, JSON-LD structured data (SoftwareApplication + FAQPage) on the
homepage, and automatic `robots.txt`/`sitemap.xml` (the sitemap includes every
guide/blog/tool page plus every active public menu URL).

Beyond the core product, a growing set of pages exist purely to attract
organic search traffic and get linked/shared:

- **Guides** (`/guides/...`) - static how-to/cost-comparison articles.
- **Blog** (`/blog/...`) - DB-backed (`blog.Post`), written either through
  Django admin or the in-app editor at `/blog/manage/`. A pre-written queue
  of marketing/ROI-angled posts (`blog/content/marketing_posts.py`) publishes
  automatically, one per day, via a GitHub Actions cron
  (`.github/workflows/daily-blog-post.yml`) that SSHes into production and
  runs `manage.py publish_next_marketing_post` — idempotent, no-ops once the
  queue is exhausted.
- **Free tools** - `/free-qr-code-generator/`, `/tools/printing-cost-calculator/`,
  `/tools/staff-efficiency-calculator/` - no login required, meant to earn
  backlinks/traffic and funnel into signup.
- **Solutions pages** - e.g. `/solutions/staff-shortage/`, a deep-dive
  landing page the homepage and blog posts link into, built around a single
  keyword theme rather than splitting the same content across multiple thin
  pages.

### 5.8 Per-restaurant subdomains

Each `Restaurant` has a unique `slug` (validated in `restaurants/forms.py`
against a DNS-safe pattern + a reserved-word blocklist - subdomains can't use
underscores even though Django's default `validate_slug` allows them). The
restaurant's menu is reachable both at `/menu/<qr_code_token>/` (existing
token-based URL, still works) and at `https://<slug>.getmenuhub.com/`.

Implementation deliberately doesn't swap `request.urlconf` per-subdomain -
`RestaurantSubdomainMiddleware` (in `menu_platform/middleware.py`) instead
inspects the `Host` header for a small, specific set of subdomain URL
patterns and calls `restaurants.views.public_menu_by_slug` directly for
those; every other path (media, static, the order API, the dashboard) falls
through completely unchanged. `Restaurant.get_subdomain_url()` builds the
canonical subdomain URL, which every public menu page's `<link rel="canonical">`
points at regardless of which of the two URLs actually served the request -
this avoids duplicate-content SEO dilution between the token URL and the
subdomain URL for the same menu.

Requires a wildcard DNS record (`*.getmenuhub.com`) and, on Railway, a plan
that allows more than one custom domain - not yet enabled on the current
plan, so this feature is code-complete but not yet reachable in production.

### 5.9 Dashboard UX & feature marketing pages

- **Table/sunbed QR cards**: `RestaurantTable.generate_qr_code()` composites
  the raw QR code onto a printable card with the restaurant's name and the
  table/sunbed label rendered on it (`restaurants/models.py::_build_table_qr_card`,
  Pillow-based, auto-shrinks the name's font to fit), so a printed stack of
  codes never gets mixed up. Reused for the restaurant's main QR too.
- **PDF menu export** (`restaurants/menu_pdf.py`, ReportLab): generated and
  streamed on request, never stored — no storage growth. Embeds DejaVu Sans
  for full Greek/Latin glyph coverage (base-14 PDF fonts don't cover Greek).
- **Dedicated feature pages** (`/features/<slug>/`,
  `menu_platform/feature_pages.py` + `feature_detail` view) — one per major
  capability (loyalty, table ordering, promo codes, analytics, staff
  management, multi-language menu), each with its own meta tags and a
  benefit-first pitch, linked from the homepage feature grid and included in
  `sitemap.xml` — built so a feature can be linked directly from an ad
  instead of always dropping traffic on the generic homepage.
- **Homepage feature grid** is grouped by customer value, not by database
  table: **Get Found** (QR code, mobile, multi-language) → **Capture the
  Order** (categories, dietary labels, table ordering) → **Bring Them Back**
  (loyalty, promo codes) → **Run the Floor** (dashboard, staff) → **Know
  Your Numbers** (analytics) — `templates/home.html`.
- **Empty states** across every list page (products, categories, orders,
  staff, promo codes, loyalty, tables, statistics) show an icon and a
  next-action line instead of plain "No X yet" text.
- **Settings** (`/restaurant/settings/`) is split into tabs (General,
  Branding, Contact, Ordering & Loyalty) as the form has grown; a validation
  error in a non-default tab auto-switches to that tab on reload so it's
  never hidden.
- **Statistics chart** (`stats_dashboard.html`) uses a gradient area fill
  under the revenue trend line with an emphasized final data point, rather
  than a bare line.

## 6. Tech Stack

- **Backend**: Django 4.2, Python 3.11
- **Database**: SQLite (dev) / PostgreSQL-ready (production, `psycopg2-binary` + `dj-database-url`)
- **Payments**: Paddle Billing API v2 (plain `requests` calls, no SDK dependency) — embedded Checkout, webhooks, Merchant of Record tax handling
- **Storage**: local filesystem (dev) / S3-compatible (production, `django-storages` + `boto3`)
- **Frontend (web)**: Server-rendered Django templates, Bootstrap 5, Bootstrap Icons, vanilla JS
  (no SPA framework), Chart.js for the stats chart
- **Mobile app**: Flutter/Dart (`mobile_app/`), Material 3, `provider` for state management,
  `http` + JWT for the API, `flutter_secure_storage` for tokens
- **Forms**: `django-crispy-forms` + `crispy-bootstrap5`
- **QR codes**: `qrcode` + `Pillow`
- **API**: Django REST Framework + `djangorestframework-simplejwt` (JWT auth for the mobile app)
- **Push notifications**: `firebase-admin` (server-side ready, inactive until a Firebase project is added)
- **Media cleanup**: `django-cleanup` (auto-deletes old media files - photos, QR codes - when replaced or the row is deleted)
- **Deployment**: `gunicorn` + `whitenoise` (static files), hosted on **Railway** (see §9)

## 7. Running locally

```bash
cd menu-platform
venv\Scripts\activate                       # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

You'll need a `.env` file in the project root (`menu-platform/.env`, not
tracked in git) with:

```
DEBUG=True
SECRET_KEY=<secret key>
ALLOWED_HOSTS=localhost,127.0.0.1
SITE_URL=http://127.0.0.1:8000    # used to build the URL embedded in QR codes

# Paddle (sandbox keys from vendors.paddle.com -> Developer Tools)
PADDLE_ENV=sandbox
PADDLE_API_KEY=pdl_sdbx_apikey_...
PADDLE_CLIENT_TOKEN=test_...
PADDLE_WEBHOOK_SECRET=ntfset_...              # from a Notification Destination in the Paddle dashboard
PADDLE_PRICE_BASIC=pri_...                    # printed by `manage.py sync_paddle_plans`
PADDLE_PRICE_PRO=pri_...
PADDLE_PRICE_BUSINESS=pri_...
```

After the first `.env` setup, run once:

```bash
python manage.py sync_paddle_plans   # creates the Paddle Products/Prices, prints the price IDs
```

To test webhooks locally, register a Notification Destination pointing at a
tunnel to `localhost:8000/accounts/webhooks/paddle/` (e.g. via ngrok) in the
Paddle sandbox dashboard - Paddle doesn't have a CLI-based local forwarder
like Stripe's.

## 8. Deployment (Railway)

Production runs on [Railway](https://railway.com) (project **GetMenuHub**,
service `Digital-QR-Platform-Global`), auto-deploying on every push to
`main`. A genuinely separate staging service (`digital-qr-platform-staging`,
its own Postgres, its own media volume, `staging` branch → auto-deploy) is
reachable at `uat-staging.getmenuhub.com` - the standard workflow is: commit
to `staging`, verify live on uat-staging, then fast-forward merge `staging`
into `main`. `railway status`/`railway logs`/`railway ssh` (CLI, run from
`menu-platform/`, pick the service+environment with `railway link` first)
are the fastest way to check deploy state or run a one-off management
command against a database - `railway ssh` in particular runs the command
**inside** the deployed container, which is required for anything touching
Postgres since `DATABASE_URL` uses Railway's internal hostname (unreachable
from outside their network, so plain `railway run` - which only injects env
vars locally - can't reach it).

GitHub Actions (`.github/workflows/ci.yml`) runs `manage.py test` on every
push/PR; `SECURE_SSL_REDIRECT` is forced `False` in CI only (it defaults
`True`-if-`DEBUG=False` otherwise, which would 301 every plain-HTTP test
request). Postgres is a separate Railway-managed service; media uploads
persist on a Railway volume mounted at `/app/media`.

The email provider in production is **Brevo** SMTP - see §5.5 for how a
Brevo outage degrades (skipped email + logged error) rather than breaking
signup/checkout.

## 9. Known limitations

- **Push notifications inactive**: the code (server + mobile) is ready but
  needs a real Firebase project to activate.
- **Loyalty/Promotions have no customer-facing UI**: the customer only sees
  their points in the order confirmation message, not in a personal account
  (no customer accounts by design, to keep the QR scan-and-order experience
  frictionless).
- **Public menu/ordering doesn't lock** if the owner's subscription expires
  (intentional, see §4.1) - only the staff dashboard locks.
- **Per-restaurant subdomains are code-complete but not live** (see §5.8) -
  blocked on a Railway plan upgrade (multiple custom domains) and the
  wildcard DNS record.
- **No email retry queue**: if an SMTP provider is down when
  welcome/admin-alert/password-changed emails are sent, that specific email
  is lost rather than retried once the provider recovers (see §5.5/§8).

### Roadmap (not yet built)

AI-based menu suggestions, inventory management, demand forecasting,
white-label branding per customer, multi-location support per business.
