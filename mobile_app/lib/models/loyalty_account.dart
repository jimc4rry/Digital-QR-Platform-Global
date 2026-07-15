/// Mirrors LoyaltyAccountSerializer / loyalty_list on the web - points per
/// customer phone number.
class LoyaltyAccount {
  final int id;
  final String phone;
  final int points;
  final DateTime createdAt;
  final DateTime updatedAt;

  LoyaltyAccount({
    required this.id,
    required this.phone,
    required this.points,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoyaltyAccount.fromJson(Map<String, dynamic> json) {
    return LoyaltyAccount(
      id: json['id'] as int,
      phone: json['phone'] as String,
      points: json['points'] as int,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}
