import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:menuhub_staff/screens/login_screen.dart';
import 'package:menuhub_staff/services/auth_service.dart';

void main() {
  Widget buildLoginScreen() {
    return ChangeNotifierProvider(
      create: (_) => AuthService(),
      child: const MaterialApp(home: LoginScreen()),
    );
  }

  testWidgets('LoginScreen shows the username/password form', (WidgetTester tester) async {
    await tester.pumpWidget(buildLoginScreen());

    expect(find.text('MenuHub'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Username'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Password'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Log In'), findsOneWidget);
  });

  testWidgets('LoginScreen validates required fields before submitting', (WidgetTester tester) async {
    await tester.pumpWidget(buildLoginScreen());

    await tester.tap(find.widgetWithText(FilledButton, 'Log In'));
    await tester.pump();

    expect(find.text('Required field'), findsNWidgets(2));
  });
}
