/// Mirrors PromoCodeSerializer / promo_code_list on the web.
class PromoCode {
  final int id;
  final String code;
  final int discountPercent;
  final bool isActive;
  final DateTime? validUntil;
  final int? maxUses;
  final int usedCount;
  final DateTime createdAt;

  PromoCode({
    required this.id,
    required this.code,
    required this.discountPercent,
    required this.isActive,
    this.validUntil,
    this.maxUses,
    required this.usedCount,
    required this.createdAt,
  });

  factory PromoCode.fromJson(Map<String, dynamic> json) {
    return PromoCode(
      id: json['id'] as int,
      code: json['code'] as String,
      discountPercent: json['discount_percent'] as int,
      isActive: json['is_active'] as bool,
      validUntil: json['valid_until'] != null ? DateTime.parse(json['valid_until'] as String) : null,
      maxUses: json['max_uses'] as int?,
      usedCount: json['used_count'] as int,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
