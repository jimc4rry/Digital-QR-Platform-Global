/// Mirrors RestaurantSettingsSerializer / restaurant_settings on the web.
class RestaurantSettings {
  final String name;
  final String description;
  final String address;
  final String phone;
  final String email;
  final bool allowOrdering;
  final bool loyaltyEnabled;
  final double taxRate;

  RestaurantSettings({
    required this.name,
    required this.description,
    required this.address,
    required this.phone,
    required this.email,
    required this.allowOrdering,
    required this.loyaltyEnabled,
    required this.taxRate,
  });

  factory RestaurantSettings.fromJson(Map<String, dynamic> json) {
    return RestaurantSettings(
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      address: json['address'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      email: json['email'] as String? ?? '',
      allowOrdering: json['allow_ordering'] as bool,
      loyaltyEnabled: json['loyalty_enabled'] as bool,
      taxRate: double.parse(json['tax_rate'].toString()),
    );
  }
}
