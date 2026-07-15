import 'api_client.dart';
import '../models/staff_user.dart';
import '../models/order.dart';
import '../models/product.dart';
import '../models/stats.dart';
import '../models/staff_member.dart';
import '../models/restaurant_settings.dart';
import '../models/loyalty_account.dart';
import '../models/promo_code.dart';

/// Groups every API call the app needs, on top of ApiClient.
class StaffRepository {
  final ApiClient _client;
  StaffRepository(this._client);

  Future<StaffUser> getMe() async {
    final data = await _client.get('/me/');
    return StaffUser.fromJson(data as Map<String, dynamic>);
  }

  Future<List<OrderSummary>> getOrders({String? status}) async {
    final data = await _client.get('/orders/', query: status != null ? {'status': status} : null);
    final results = (data as Map<String, dynamic>)['results'] as List<dynamic>;
    return results.map((e) => OrderSummary.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<OrderDetail> getOrderDetail(int orderId) async {
    final data = await _client.get('/orders/$orderId/');
    return OrderDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<OrderDetail> updateOrderStatus(int orderId, String newStatus) async {
    final data = await _client.post('/orders/$orderId/status/', body: {'status': newStatus});
    return OrderDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Product>> getProducts() async {
    final data = await _client.get('/products/');
    final results = (data as Map<String, dynamic>)['results'] as List<dynamic>;
    return results.map((e) => Product.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Product> setProductAvailability(int productId, bool isAvailable) async {
    final data = await _client.post(
      '/products/$productId/availability/',
      body: {'is_available': isAvailable},
    );
    return Product.fromJson(data as Map<String, dynamic>);
  }

  Future<void> registerDeviceToken(String token, String platform) async {
    await _client.post('/device-tokens/', body: {'token': token, 'platform': platform});
  }

  Future<Stats> getStats() async {
    final data = await _client.get('/stats/');
    return Stats.fromJson(data as Map<String, dynamic>);
  }

  Future<(bool, List<StaffMember>)> getStaff() async {
    final data = await _client.get('/staff/') as Map<String, dynamic>;
    final available = data['available'] as bool;
    final results = (data['results'] as List<dynamic>)
        .map((e) => StaffMember.fromJson(e as Map<String, dynamic>))
        .toList();
    return (available, results);
  }

  Future<StaffMember> createStaff(String username, String password, String role) async {
    final data = await _client.post('/staff/', body: {
      'username': username,
      'password': password,
      'role': role,
    });
    return StaffMember.fromJson(data as Map<String, dynamic>);
  }

  Future<void> deleteStaff(int staffId) async {
    await _client.delete('/staff/$staffId/');
  }

  Future<RestaurantSettings> getSettings() async {
    final data = await _client.get('/settings/');
    return RestaurantSettings.fromJson(data as Map<String, dynamic>);
  }

  Future<RestaurantSettings> updateSettings(Map<String, dynamic> fields) async {
    final data = await _client.patch('/settings/', body: fields);
    return RestaurantSettings.fromJson(data as Map<String, dynamic>);
  }

  Future<(bool, List<LoyaltyAccount>)> getLoyaltyAccounts({String? search}) async {
    final data = await _client.get('/loyalty/', query: search != null && search.isNotEmpty ? {'q': search} : null)
        as Map<String, dynamic>;
    final available = data['available'] as bool;
    final results = (data['results'] as List<dynamic>)
        .map((e) => LoyaltyAccount.fromJson(e as Map<String, dynamic>))
        .toList();
    return (available, results);
  }

  Future<LoyaltyAccount> updateLoyaltyPoints(int accountId, int points) async {
    final data = await _client.patch('/loyalty/$accountId/', body: {'points': points});
    return LoyaltyAccount.fromJson(data as Map<String, dynamic>);
  }

  Future<void> deleteLoyaltyAccount(int accountId) async {
    await _client.delete('/loyalty/$accountId/');
  }

  Future<(bool, List<PromoCode>)> getPromoCodes() async {
    final data = await _client.get('/promo-codes/') as Map<String, dynamic>;
    final available = data['available'] as bool;
    final results = (data['results'] as List<dynamic>)
        .map((e) => PromoCode.fromJson(e as Map<String, dynamic>))
        .toList();
    return (available, results);
  }

  Future<PromoCode> createPromoCode({
    required String code,
    required int discountPercent,
    int? maxUses,
  }) async {
    final data = await _client.post('/promo-codes/', body: {
      'code': code,
      'discount_percent': discountPercent,
      if (maxUses != null) 'max_uses': maxUses,
    });
    return PromoCode.fromJson(data as Map<String, dynamic>);
  }

  Future<void> deletePromoCode(int promoId) async {
    await _client.delete('/promo-codes/$promoId/');
  }
}
