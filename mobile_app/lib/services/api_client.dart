import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import 'auth_service.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

/// Thin wrapper around http that attaches the JWT and retries once after a
/// silent token refresh if the server says the access token expired.
class ApiClient {
  final AuthService authService;
  ApiClient(this.authService);

  Future<dynamic> get(String path, {Map<String, String>? query}) {
    return _request('GET', path, query: query);
  }

  Future<dynamic> post(String path, {Map<String, dynamic>? body}) {
    return _request('POST', path, body: body);
  }

  Future<dynamic> patch(String path, {Map<String, dynamic>? body}) {
    return _request('PATCH', path, body: body);
  }

  Future<dynamic> delete(String path) {
    return _request('DELETE', path);
  }

  Future<dynamic> _request(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
    bool isRetry = false,
  }) async {
    final uri = Uri.parse('${ApiConfig.apiBaseUrl}$path').replace(queryParameters: query);
    final headers = {
      'Content-Type': 'application/json',
      if (authService.accessToken != null) 'Authorization': 'Bearer ${authService.accessToken}',
    };

    late http.Response response;
    final encodedBody = body != null ? jsonEncode(body) : null;

    switch (method) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(uri, headers: headers, body: encodedBody);
        break;
      case 'PATCH':
        response = await http.patch(uri, headers: headers, body: encodedBody);
        break;
      case 'DELETE':
        response = await http.delete(uri, headers: headers);
        break;
      default:
        throw ApiException(0, 'Unsupported method $method');
    }

    if (response.statusCode == 401 && !isRetry) {
      final refreshed = await authService.refreshAccessToken();
      if (refreshed) {
        return _request(method, path, query: query, body: body, isRetry: true);
      }
      throw ApiException(401, 'Session expired. Please log in again.');
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(utf8.decode(response.bodyBytes));
    }

    String message = 'Error (${response.statusCode})';
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is Map && decoded.isNotEmpty) {
        message = decoded.values.first.toString();
      }
    } catch (_) {
      // keep default message
    }
    throw ApiException(response.statusCode, message);
  }
}
