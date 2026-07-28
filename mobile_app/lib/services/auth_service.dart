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
        // The backend rotates the refresh token on every use (and blacklists
        // the old one) - the old token stops working after this point, so it
        // must be persisted or the *next* refresh call fails as if logged out.
        final rotatedRefresh = data['refresh'] as String?;
        if (rotatedRefresh != null) {
          await _storage.write(key: _refreshKey, value: rotatedRefresh);
        }
        notifyListeners();
        return true;
      }
    } catch (_) {
      // fall through to logout
    }
    await logout();
    return false;
  }

  /// Tells the backend to blacklist the current refresh token before
  /// clearing local storage, so a logged-out session can't be replayed if the
  /// token leaked (e.g. from a lost/reset device). Best-effort - local
  /// storage is always cleared even if the server call fails (offline, etc.).
  Future<void> logout() async {
    final refreshToken = await _storage.read(key: _refreshKey);
    final currentAccess = _accessToken;
    if (refreshToken != null && currentAccess != null) {
      try {
        await http.post(
          Uri.parse('${ApiConfig.apiBaseUrl}/auth/logout/'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $currentAccess',
          },
          body: jsonEncode({'refresh': refreshToken}),
        );
      } catch (_) {
        // offline or server unreachable - still clear the local session below
      }
    }

    _accessToken = null;
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    notifyListeners();
  }
}
