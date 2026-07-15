import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/auth_service.dart';
import 'screens/login_screen.dart';
import 'screens/order_list_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const MenuHubStaffApp());
}

class MenuHubStaffApp extends StatelessWidget {
  const MenuHubStaffApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthService(),
      child: MaterialApp(
        title: 'MenuHub Staff',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        themeMode: ThemeMode.system,
        home: const _StartupGate(),
      ),
    );
  }
}

/// Waits for the securely-stored session to load, then routes to login or
/// straight to the order list if a token is already saved on this device.
class _StartupGate extends StatefulWidget {
  const _StartupGate();

  @override
  State<_StartupGate> createState() => _StartupGateState();
}

class _StartupGateState extends State<_StartupGate> {
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    context.read<AuthService>().loadStoredSession().then((_) {
      if (mounted) setState(() => _ready = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.qr_code_2_rounded, size: 40, color: Theme.of(context).colorScheme.onPrimaryContainer),
              ),
              const SizedBox(height: 20),
              const CircularProgressIndicator(),
            ],
          ),
        ),
      );
    }
    final isLoggedIn = context.watch<AuthService>().isLoggedIn;
    return isLoggedIn ? const OrderListScreen() : const LoginScreen();
  }
}
