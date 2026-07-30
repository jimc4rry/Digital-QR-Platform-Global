# GetMenuHub — Product Showcase & Marketing Kit

This is a visual walkthrough of the live product, captured from a fully
populated demo account ("Aegean Breeze Café" — a seaside cafe with a real
menu, tables, staff, orders and loyalty customers), so every screenshot
below reflects the actual app, not a mockup. It's meant as a starting kit
for advertising: use the screenshots directly in ads/landing pages, and use
the positioning notes at the end to write copy.

> The engineering documentation lives in
> [`menu-platform/README.md`](menu-platform/README.md). This file is the
> product/marketing companion to it.

## Contents

1. [The pitch, in one paragraph](#the-pitch-in-one-paragraph)
2. [The customer experience](#1-the-customer-experience)
3. [Getting started: the dashboard](#2-getting-started-the-dashboard)
4. [Building the menu](#3-building-the-menu)
5. [Taking orders](#4-taking-orders)
6. [Growth tools: loyalty & promo codes](#5-growth-tools-loyalty--promo-codes)
7. [Managing the team](#6-managing-the-team)
8. [Understanding the business: statistics](#7-understanding-the-business-statistics)
9. [Branding, QR codes & settings](#8-branding-qr-codes--settings)
10. [The marketing site](#9-the-marketing-site)
11. [Mobile & dark mode](#10-mobile--dark-mode)
12. [Ready to advertise](#11-ready-to-advertise)

---

## The pitch, in one paragraph

GetMenuHub is a restaurant growth platform disguised as a QR menu: a business
signs up, builds a menu in minutes, and gets a QR code that replaces printed
menus forever — but underneath that is a full toolkit that keeps customers
coming back and keeps the owner in control: table-side ordering with zero
commission, a loyalty program that needs no app, promo codes for slow
nights, role-based staff accounts, and sales analytics. Every plan includes
the digital menu; Pro and Business unlock the growth layer on top.

---

## 1. The customer experience

This is what a customer sees after scanning the QR code on their table —
no app, no login, opens straight in their phone's browser.

![Public menu — full storefront](docs/showcase/15-public-menu.png)

*The storefront carries the restaurant's own logo, cover photo, and
description — it reads as the restaurant's own site, not a third-party
tool. Categories are sticky-tabbed at the top so a long menu never feels
long.*

When a table's own QR code is scanned (not the general one), ordering
unlocks: customers pick product options — like size, milk, or sweetness —
add items to a running cart, and send the order straight to the kitchen.

![Cart with product options and table number pre-filled](docs/showcase/20-table-order-cart.png)

*Product options are configured once by the owner (see [§3](#3-building-the-menu))
and rendered automatically as radio groups (mutually exclusive, like
"Sweetness: Plain / Light / Sweet") or checkboxes (independent add-ons,
like "Add poached egg"). Price is always recalculated server-side, so a
customer can never manipulate the total. The table number arrives
pre-filled from the QR code the customer actually scanned.*

On a phone, the same page collapses into a clean single-column layout with
a floating cart bar:

![Mobile public menu](docs/showcase/18-mobile-public-menu.png)

---

## 2. Getting started: the dashboard

After signup, the owner lands here. Every stat updates in real time, and a
checklist (category → product → table → preview) walks a brand-new account
through activation — it disappears automatically once done, so a returning
owner never sees stale onboarding noise.

![Owner dashboard](docs/showcase/03-dashboard.png)

*Notice the navigation: six grouped items (Dashboard, Menu, Orders, Growth,
Statistics, Staff) instead of a flat wall of links. The marketing site's
own navigation (Blog, Guides, pricing calculators) disappears the instant
someone is logged into the app — a logged-in owner mid-shift never has to
scan past content meant for a prospect still deciding whether to sign up.*

---

## 3. Building the menu

Categories and products are managed from dedicated pages, each with the
create-form and the list side by side so nothing requires a page reload.

![Products page with bulk actions](docs/showcase/04-products.png)

*At scale (40–80 items on a busy weekend) this page is built for speed:
search by name, filter by category, and — new this release — select
multiple products at once to mark them available/unavailable, move them to
another category, or delete them in one action. Every product supports a
photo, a description, dietary labels (vegan/vegetarian/gluten-free/spicy),
an old-price for showing a discount, and mutually-exclusive or independent
option groups.*

![Categories with reordering](docs/showcase/05-categories.png)

*Categories can be reordered with a click, and any product left orphaned by
a deleted category is automatically reassigned to an "Other" bucket instead
of silently disappearing.*

---

## 4. Taking orders

Every order — whether the customer placed it themselves from a table QR
code, or staff took it by phone — lands in the same place.

![Orders list](docs/showcase/06-orders.png)

Staff and admins can also build an order themselves — for a phone order, a
walk-in, or a customer who'd rather just ask someone — using the exact same
product picker and pricing engine as the public menu:

![Staff-facing New Order screen](docs/showcase/07-new-order.png)

Every order has a detail page with full status history — who changed it,
and when:

![Order detail](docs/showcase/08-order-detail.png)

---

## 5. Growth tools: loyalty & promo codes

These are the two most under-marketed features in the product relative to
how much value they add — see [§11](#11-ready-to-advertise) for how to sell
them.

![Promo codes](docs/showcase/10-promo-codes.png)

*A promo code is created in seconds — a percentage off, an optional usage
cap, an optional expiry date — and can be sent selectively (a slow Tuesday,
a specific regular) instead of discounting every night out of habit.*

![Customer loyalty ranking](docs/showcase/11-loyalty.png)

*No app, no card, nothing for the customer to install: loyalty accounts are
created automatically the first time a customer leaves their phone number
with an order, and every point after that is tracked against that number.
The owner sees a live ranking of their best customers.*

---

## 6. Managing the team

Each staff member gets their own login instead of a shared password —
Admins manage the menu and settings, Employees just handle orders.

![Staff management](docs/showcase/12-staff.png)

---

## 7. Understanding the business: statistics

Revenue for today/this week/this month, a 14-day trend chart, and a live
ranking of best-selling products — built from orders the business is
already taking, with nothing to maintain.

![Sales statistics](docs/showcase/13-statistics.png)

*Every order can also be exported to CSV for the owner's own bookkeeping.*

---

## 8. Branding, QR codes & settings

Every table and sunbed gets its own printable QR code — with the
restaurant's name and the table label printed directly on the card, so a
stack of them never gets mixed up in the kitchen.

![Tables & QR codes](docs/showcase/09-tables-qr.png)

Restaurant settings are grouped into tabs as the form has grown — General,
Branding, Contact, Ordering & Loyalty — so no single page feels
overwhelming.

![Settings, tabbed](docs/showcase/14-settings.png)

---

## 9. The marketing site

The homepage leads with the full platform, not just the menu — and
foregrounds the free-beta offer instead of burying it in a banner:

![Homepage](docs/showcase/01-homepage.png)

Every major feature also has its own dedicated landing page — good for SEO,
and good for linking directly from an ad instead of dropping traffic on the
generic homepage:

![Feature page example — Loyalty](docs/showcase/16-feature-page.png)

Dark mode is a genuine, fully-designed second theme, not a filter:

![Homepage, dark mode](docs/showcase/19-dark-mode-homepage.png)

Login is a single clean form — no distractions between an existing owner
and their dashboard:

![Login](docs/showcase/02-login.png)

---

## 10. Mobile & dark mode

Every screen shown above — marketing site, dashboard, customer menu — is
fully responsive. This is the homepage on a phone:

![Mobile homepage](docs/showcase/17-mobile-homepage.png)

---

## 11. Ready to advertise

A few notes to turn the screenshots above into actual ads, written from a
"what would make a restaurant owner stop scrolling" perspective.

### Who to target

- **Independent cafés, bars, tavernas and beach bars** — 1–3 locations, no
  in-house tech team. This is the product's real sweet spot: simple enough
  to set up alone in 5 minutes, no POS integration required, no sales call.
- **Seasonal / tourist-facing venues** (beach bars, hotel cafés) — the
  sunbed QR-ordering angle is close to unique; almost no competitor markets
  it explicitly.
- **Owners currently paying for printing** — every reprint (a price change,
  a seasonal menu, a translation) is a repeat cost this replaces entirely.
- **Short-staffed venues** — table-side ordering is a genuine labor-saving
  feature, not just a novelty; lead with this for owners who are visibly
  struggling to hire.

### The core hook (use this before anything else)

> **Menu, orders, loyalty and staff — all from one QR code.**

This single line does the most work: it opens with the QR code (which every
restaurant owner already recognizes and associates with "modern"), and
closes the sentence by revealing the platform is bigger than a menu, before
anyone can dismiss it as "just another QR menu app."

### Sample ad copy

**Meta / Instagram (feed, square or 4:5 image — use the public-menu or
table-order-cart screenshot):**

> Your menu, always up to date. Orders straight from the table. Customers
> who actually come back. One QR code does it all — set up free in 5
> minutes, no printer, no app for your customers to download.
> **Create your free menu →**

**Meta / Instagram, staffing angle (use the dashboard or new-order screenshot):**

> Short-staffed? Let customers order themselves. Table-side ordering means
> fewer trips back and forth for your team — and it's free to try, every
> feature unlocked.
> **See how it works →**

**Google Search ad (headline / description pairs):**

- H1: `QR Menu + Table Ordering` · H2: `Free During Beta — No Card` ·
  Desc: `Digital menu, orders, loyalty & staff tools in one dashboard. Set up in 5 minutes.`
- H1: `Stop Reprinting Your Menu` · H2: `Update Prices Instantly` ·
  Desc: `QR code menu with zero reprinting. Every plan feature free during beta.`

**Greek-language variant (for local/tourist-area targeting):**

> Το μενού σας πάντα ενημερωμένο, παραγγελίες από το τραπέζι, πελάτες που
> ξαναγυρνάνε. Όλα από έναν κωδικό QR. Δωρεάν δοκιμή, χωρίς κάρτα.
> **Δημιουργήστε το δωρεάν μενού σας →**

### Which screenshot to use for which angle

| Angle | Screenshot |
|---|---|
| "It's a real, modern menu" | [public menu](docs/showcase/15-public-menu.png) |
| "Ordering just works" | [table order cart](docs/showcase/20-table-order-cart.png) |
| "It's not just a menu tool" | [dashboard](docs/showcase/03-dashboard.png) or [statistics](docs/showcase/13-statistics.png) |
| "Customers come back" | [loyalty](docs/showcase/11-loyalty.png) |
| "Built for a real team" | [staff](docs/showcase/12-staff.png) or [new order](docs/showcase/07-new-order.png) |
| "Works everywhere, looks modern" | [mobile homepage](docs/showcase/17-mobile-homepage.png) or [dark mode](docs/showcase/19-dark-mode-homepage.png) |

### Landing page discipline

Send every ad to the **matching page**, not always the homepage:

- A loyalty-angled ad → `/features/loyalty-program/`
- A staffing/labor-angled ad → `/solutions/staff-shortage/`
- A general "what is this" ad → the homepage
- A "switching from X" search ad (once written) → a comparison page

This keeps the promise made in the ad and the first thing the visitor sees
in sync — the single highest-leverage thing for conversion rate, more than
any copy tweak on the page itself.

### One honest gap to close before spending real ad budget

There are currently no real customer testimonials or logos anywhere on the
site. This is the single biggest lever left — even one short, named quote
("Aegean Breeze Café cut order-taking time in half — Maria K., owner")
will outperform any copy or design change above it. Get this from the
first few real signups before scaling paid spend.
