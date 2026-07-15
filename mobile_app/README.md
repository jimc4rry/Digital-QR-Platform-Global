# MenuHub Staff App (Flutter)

App for restaurant owners/staff - manage orders and products from your phone,
on the **same database** as the web dashboard (menu-platform/). It doesn't
change anything in the existing Django project - it talks to it through a
REST API layer (`menu-platform/api/`).

## What's already built (backend, in menu-platform/)

- `api/` Django app: JWT login, `/me/`, orders (list/detail/status change),
  products (list/toggle availability), categories, push token registration.
- Same role system (owner/admin/employee) as the web - whatever you can't see
  on the dashboard, you can't see in the app either.
- Push notifications (Firebase) - the backend hook exists, inactive until you
  add Firebase credentials (see below).

## How to run it

You need the [Flutter SDK](https://docs.flutter.dev/get-started/install) installed.

```bash
cd mobile_app
flutter pub get
flutter run
```

### 1. Set the server address

Open [`lib/config/api_config.dart`](lib/config/api_config.dart) and set the
right IP:

- **Android emulator** (talking to your PC): `http://10.0.2.2:8000`
- **Real phone on the same Wi-Fi**: `http://<YOUR_LAN_IP>:8000`
- **iOS simulator**: `http://127.0.0.1:8000`

The Django server needs to run with `python manage.py runserver 0.0.0.0:8000`
(`start_server_lan.bat` in `menu-platform/` already does exactly that).

### 2. Log in

Use the same login credentials (username/password) that the owner/admin/
employee already has for the web dashboard - it's the same account, same
database.

## Project structure

```
lib/
  config/api_config.dart       # Backend address
  models/                      # StaffUser, Order, Product (match the API JSON)
  services/
    auth_service.dart          # Login/logout, JWT storage (flutter_secure_storage)
    api_client.dart            # HTTP wrapper with auto-refresh token
    staff_repository.dart      # All API calls in one place
  screens/
    login_screen.dart
    order_list_screen.dart     # Order list with status filter
    order_detail_screen.dart   # Details + status change + activity log
    product_list_screen.dart   # Product list + on/off availability
```

## Push notifications setup (optional)

The backend is ready to send a push when a new order comes in, but needs a
real Firebase project (this step is yours to do, it requires your own Google
account):

1. Create a project on the [Firebase Console](https://console.firebase.google.com/).
2. Add an Android app (`com.menuhub.staff` or whatever package name you pick) and an iOS app.
3. Download `google-services.json` (Android) → `android/app/`, and `GoogleService-Info.plist` (iOS) → `ios/Runner/`.
4. In the Firebase Console → Project Settings → Service Accounts → "Generate new private key" → download the JSON.
5. In `menu-platform/.env`, add: `FIREBASE_CREDENTIALS_PATH=/absolute/path/to/service-account.json`
6. In `mobile_app/pubspec.yaml`, uncomment `firebase_core`/`firebase_messaging`, run `flutter pub get`.
7. You'll need a bit more code in `main.dart` (Firebase init) and a `PushService`
   that calls `POST /api/v1/device-tokens/` with the device token.

Until then, the app works normally - you just won't get push notifications,
you'll see new orders via pull-to-refresh on the list.
