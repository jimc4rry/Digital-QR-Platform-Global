# MenuHub — Digital QR Code Menus for Restaurants, Cafes, Bars & Beach Bars

Django SaaS platform that lets restaurants/cafes/bars/beach bars create a
digital menu accessible via QR code, with optional online ordering (from a
table **or** a sunbed), staff management, loyalty points, discount codes,
sales statistics, and real subscription billing via **Paddle** (Merchant of
Record — handles international VAT/sales tax automatically). Includes a
separate mobile app (Flutter) for owners/staff.

This is the **Global edition** of MenuHub: English-only, available to
businesses worldwide, billed in USD through Paddle. It was forked from the
original Greek-market edition (Stripe billing, Greek Tax ID requirement,
Greek-only dashboard) — same feature set, adapted for an international
audience.

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
statistics, and their subscription.

## 2. User Flow

### A. Restaurant Owner
1. **Sign up** (`/accounts/signup/`) — creates a user account. A `Restaurant`
   is created **automatically** at the same time (1-to-1 `User` ↔
   `Restaurant` relationship), with a random `qr_code_token` and a QR code
   image generated on the model's first `save()`. The account starts with a
   **30-day free trial** on the Basic plan (`subscription_active=True`,
   `subscription_ends=+30d`).
2. **Creates Categories** (e.g. "Starters", "Mains") and **Products** (price,
   photo, dietary labels: vegan/vegetarian/gluten-free/spicy, optional
   per-product "options" like size/filling with a price adjustment).
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
menu_platform/   # project config: settings, root urls, wsgi/asgi, seo_views (robots.txt/sitemap.xml)
accounts/        # custom User model, signup/login/password-change, Paddle billing (billing.py,
                 # checkout/webhook/portal views), Payment model, management command sync_paddle_plans
restaurants/     # Restaurant, Category, Product, ProductOption, StaffMember, RestaurantTable
                 # (table/sunbed), PromoCode, LoyaltyAccount + all owner/admin/employee views
orders/          # Order, OrderItem, OrderStatusLog + public ordering API + reports
api/             # REST API (DRF + JWT) for the Flutter staff app - /api/v1/..., same DB/models
templates/       # all HTML templates (split per app + shared base.html)
locale/en/       # gettext .po/.mo translations (kept as the runtime i18n mechanism; the site
                 # renders English-only via LANGUAGE_CODE='en' / LANGUAGES=[('en', 'English')])
static/          # static assets
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
| Email | Console backend (prints to terminal) | Needs a real `EMAIL_BACKEND`/SMTP config before production |
| Payments | Paddle **sandbox** (`PADDLE_ENV=sandbox`) | Same code, just live keys (`PADDLE_ENV=production`) + a real webhook endpoint registered in the Paddle dashboard |
| Static files | WhiteNoise | Already production-ready |
| Cookie/HSTS security | Off under `DEBUG=True` | Turned on automatically when `DEBUG=False` |

None of these changes need a code change - only environment variables.

### 5.6 Internationalization (i18n)

The Global edition is **English-only**: `LANGUAGE_CODE='en'` and
`LANGUAGES=[('en', 'English')]` in settings. Under the hood the app still
uses Django's `gettext` machinery (`{% trans %}`/`{% blocktrans %}` +
`LocaleMiddleware`) with translations compiled into
`locale/en/LC_MESSAGES/django.mo` - this was inherited from the original
bilingual (Greek/English) edition and simply renders English everywhere now
that English is the only configured language. There's no language switcher
in the UI since there's only one language available.

### 5.7 SEO

Dynamic meta tags (title/description/OG/canonical) via template blocks in
`base.html`, JSON-LD structured data (SoftwareApplication + FAQPage) on the
homepage, and automatic `robots.txt`/`sitemap.xml` (the sitemap includes every
active public menu URL).

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
- **Deployment**: `gunicorn` + `whitenoise` (static files)

> ⚠️ `django-cleanup` is in `requirements.txt` but is **not** registered in
> `INSTALLED_APPS` - currently inert (old media files aren't auto-deleted
> when replaced). Either add it to `INSTALLED_APPS` or remove it from
> requirements.

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

## 8. Known limitations

- **Email via console backend**: order notifications print to the terminal
  instead of actually being sent, until a real SMTP config is set in production.
- **Push notifications inactive**: the code (server + mobile) is ready but
  needs a real Firebase project to activate.
- **Loyalty/Promotions have no customer-facing UI**: the customer only sees
  their points in the order confirmation message, not in a personal account
  (no customer accounts by design, to keep the QR scan-and-order experience
  frictionless).
- **Public menu/ordering doesn't lock** if the owner's subscription expires
  (intentional, see §4.1) - only the staff dashboard locks.

### Roadmap (not yet built)

AI-based menu suggestions, inventory management, demand forecasting,
white-label branding per customer, multi-location support per business.
