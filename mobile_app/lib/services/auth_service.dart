import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

/// Holds the JWT pair and exposes login/logout. Registered as a
/// ChangeNotifierProvider in main.dart so screens can watch isLoggedIn.
class AuthService extends ChangeNotifier {
  final _storage = const FlutterSecureStorage();
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  String? _accessToken;
  String? get accessToken => _accessToken;
  bool get isLoggedIn => _accessToken != null;

  Future<void> loadStoredSession() async {
    _accessToken = await _storage.read(key: _accessKey);
    notifyListeners();
  }

  /// Returns null on success, or a human-readable error message on failure.
  Future<String?> login(String username, String password) async {
    final uri = Uri.parse('${ApiConfig.apiBaseUrl}/auth/login/');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _accessToken = data['access'] as String;
        await _storage.write(key: _accessKey, value: _accessToken);
        await _storage.write(key: _refreshKey, value: data['refresh'] as String);
        notifyListeners();
        return null;
      }
      if (response.statusCode == 401) {
        return 'Incorrect username or password.';
      }
      return 'Something went wrong (${response.statusCode}). Please try again.';
    } catch (e) {
      return 'Connection error. Make sure the server is running and the IP in api_config.dart is correct.';
    }
  }

  Future<bool> refreshAccessToken() async {
    final refreshToken = await _storage.read(key: _refreshKey);
    if (refreshToken == null) return false;

    final uri = Uri.parse('${ApiConfig.apiBaseUrl}/auth/refresh/');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refreshToken}),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _accessToken = data['access'] as String;
        await _storage.write(key: _accessKey, value: _accessToken);
        notifyListeners();
        return true;
      }
    } catch (_) {
      // fall through to logout
    }
    await logout();
    return false;
  }

  Future<void> logout() async {
    _accessToken = null;
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    notifyListeners();
  }
}
