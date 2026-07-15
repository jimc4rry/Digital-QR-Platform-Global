/// Mirrors the JSON returned by GET /api/v1/me/ - the same permission flags
/// the Django web dashboard computes in restaurants/context_processors.py.
class StaffUser {
  final String username;
  final String role; // 'owner' | 'admin' | 'employee'
  final int restaurantId;
  final String restaurantName;
  final bool canManageMenu;
  final bool canUseProFeatures;
  final bool canViewStats;
  final bool canManageStaff;
  final bool restaurantAcceptsOrders;

  StaffUser({
    required this.username,
    required this.role,
    required this.restaurantId,
    required this.restaurantName,
    required this.canManageMenu,
    required this.canUseProFeatures,
    required this.canViewStats,
    required this.canManageStaff,
    required this.restaurantAcceptsOrders,
  });

  factory StaffUser.fromJson(Map<String, dynamic> json) {
    return StaffUser(
      username: json['username'] as String,
      role: json['role'] as String,
      restaurantId: json['restaurant_id'] as int,
      restaurantName: json['restaurant_name'] as String,
      canManageMenu: json['can_manage_menu'] as bool,
      canUseProFeatures: json['can_use_pro_features'] as bool,
      canViewStats: json['can_view_stats'] as bool,
      canManageStaff: json['can_manage_staff'] as bool,
      restaurantAcceptsOrders: json['restaurant_accepts_orders'] as bool,
    );
  }

  bool get isOwner => role == 'owner';
  bool get isEmployee => role == 'employee';
}
