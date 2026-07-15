import 'package:flutter/material.dart';
import '../models/staff_user.dart';
import '../services/staff_repository.dart';
import 'stats_screen.dart';
import 'staff_management_screen.dart';
import 'restaurant_settings_screen.dart';
import 'loyalty_promo_screen.dart';

/// Entry point for owner/admin-only tools that mirror the web dashboard's
/// nav items: stats, staff, settings, loyalty & promo codes.
class OwnerToolsScreen extends StatelessWidget {
  final StaffUser me;
  final StaffRepository repository;

  const OwnerToolsScreen({super.key, required this.me, required this.repository});

  @override
  Widget build(BuildContext context) {
    final tiles = [
      _ToolTileData(
        icon: Icons.bar_chart_rounded,
        color: Colors.indigo,
        title: 'Statistics',
        subtitle: 'Sales & revenue',
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => StatsScreen(repository: repository)),
        ),
      ),
      if (me.isOwner)
        _ToolTileData(
          icon: Icons.people_alt_rounded,
          color: Colors.teal,
          title: 'Staff',
          subtitle: 'Admins & employees',
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => StaffManagementScreen(repository: repository)),
          ),
        ),
      _ToolTileData(
        icon: Icons.settings_rounded,
        color: Colors.orange,
        title: 'Settings',
        subtitle: 'Restaurant details',
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => RestaurantSettingsScreen(repository: repository)),
        ),
      ),
      _ToolTileData(
        icon: Icons.star_rounded,
        color: Colors.pink,
        title: 'Loyalty & Promo',
        subtitle: 'Points & discounts',
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => LoyaltyPromoScreen(repository: repository)),
        ),
      ),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Management')),
      body: GridView.count(
        padding: const EdgeInsets.all(16),
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 1.05,
        children: tiles.map((t) => _ToolTile(data: t)).toList(),
      ),
    );
  }
}

class _ToolTileData {
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  _ToolTileData({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });
}

class _ToolTile extends StatelessWidget {
  final _ToolTileData data;
  const _ToolTile({required this.data});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: data.onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: data.color.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(data.icon, color: data.color, size: 24),
              ),
              const Spacer(),
              Text(data.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
              const SizedBox(height: 2),
              Text(
                data.subtitle,
                style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Shown by feature screens when the restaurant's plan doesn't include this
/// feature yet - mirrors feature_upgrade.html on the web.
class UpgradeRequiredView extends StatelessWidget {
  final String message;
  const UpgradeRequiredView({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: scheme.primaryContainer, shape: BoxShape.circle),
              child: Icon(Icons.workspace_premium_rounded, size: 36, color: scheme.onPrimaryContainer),
            ),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center, style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 15)),
          ],
        ),
      ),
    );
  }
}
