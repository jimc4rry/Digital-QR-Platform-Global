/// Central place for the backend address. Change this to match how you're
/// running the Django server:
///  - Android emulator talking to your PC:      http://10.0.2.2:8000
///  - Real phone on the same Wi-Fi as your PC:   http://<YOUR_LAN_IP>:8000
///  - iOS simulator:                             http://127.0.0.1:8000
///  - Production:                                https://your-domain.com
class ApiConfig {
  static const String baseUrl = 'http://192.168.1.71:8000';
  static const String apiPrefix = '/api/v1';

  static String get apiBaseUrl => '$baseUrl$apiPrefix';
}
