import 'package:flutter_test/flutter_test.dart';

import 'package:stock_frontend/main.dart';

void main() {
  testWidgets('FinTossApp renders home screen', (WidgetTester tester) async {
    await tester.pumpWidget(const FinTossApp());

    expect(find.text('Stockky'), findsOneWidget);
    expect(find.text('Total Assets'), findsOneWidget);
  });
}
