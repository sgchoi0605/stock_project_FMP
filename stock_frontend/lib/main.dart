import 'package:flutter/material.dart';
import 'services/service.dart' as service;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      home: FinancialScreen(),
    );
  }
}

class FinancialScreen extends StatefulWidget {
  const FinancialScreen({super.key});

  @override
  State<FinancialScreen> createState() => _FinancialScreenState();
}

class _FinancialScreenState extends State<FinancialScreen> {
  late Future<List<dynamic>> financials;

  @override
  void initState() {
    super.initState();
    financials = service.ApiService.fetchFinancials("AAPL");
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Financial Statements'),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: financials,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Text(snapshot.error.toString()),
            );
          }

          final data = snapshot.data!;

          return ListView.builder(
            itemCount: data.length,
            itemBuilder: (context, index) {
              final item = data[index];

              return ListTile(
                title: Text(item['calendarYear']?.toString() ?? 'N/A'),
                subtitle: Text(
                  'Revenue: ${item['revenue']}\n'
                  'Operating Income: ${item['operatingIncome']}',
                ),
              );
            },
          );
        },


      ),
    );
  }
}


// 실행 : dart 터미널에서 flutter run -d chrome
