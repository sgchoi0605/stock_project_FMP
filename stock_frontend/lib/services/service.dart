import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  static Future<List<dynamic>> fetchFinancials(String symbol) async {
    final response = await http.get(
      Uri.parse('$baseUrl/financials/$symbol'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load financials: ${response.statusCode} ${response.body}');
    }
  }

  static Future<List<StockSearchItem>> searchStocks(String query, {int limit = 20}) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      return const [];
    }

    final uri = Uri.parse('$baseUrl/search-stocks/$trimmed?limit=$limit');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception('Failed to search stocks: ${response.statusCode} ${response.body}');
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! List) {
      return const [];
    }

    return decoded
        .whereType<Map<String, dynamic>>()
        .map(StockSearchItem.fromJson)
        .toList();
  }

  static Future<StockDetailItem> fetchStockDetail(String symbol) async {
    final trimmed = symbol.trim();
    if (trimmed.isEmpty) {
      throw Exception('Symbol is empty.');
    }

    final uri = Uri.parse('$baseUrl/stock/$trimmed');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception('Failed to fetch stock detail: ${response.statusCode} ${response.body}');
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Invalid stock detail response.');
    }

    return StockDetailItem.fromJson(decoded);
  }
}

class StockSearchItem {
  const StockSearchItem({
    required this.symbol,
    required this.name,
    required this.price,
    required this.changePercentage,
  });

  final String symbol;
  final String name;
  final double? price;
  final double? changePercentage;

  factory StockSearchItem.fromJson(Map<String, dynamic> json) {
    return StockSearchItem(
      symbol: (json['symbol'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      price: _toDouble(json['price']),
      changePercentage: _toDouble(json['changePercentage']),
    );
  }

  static double? _toDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }
    final raw = value?.toString() ?? '';
    final sanitized = raw.replaceAll('%', '').trim();
    return double.tryParse(sanitized);
  }
}

class StockDetailItem {
  const StockDetailItem({
    required this.symbol,
    required this.name,
    required this.price,
    required this.changePercentage,
    required this.open,
    required this.dayHigh,
    required this.dayLow,
    required this.previousClose,
    required this.volume,
  });

  final String symbol;
  final String name;
  final double? price;
  final double? changePercentage;
  final double? open;
  final double? dayHigh;
  final double? dayLow;
  final double? previousClose;
  final double? volume;

  factory StockDetailItem.fromJson(Map<String, dynamic> json) {
    return StockDetailItem(
      symbol: (json['symbol'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      price: StockSearchItem._toDouble(json['price']),
      changePercentage: StockSearchItem._toDouble(json['changePercentage']),
      open: StockSearchItem._toDouble(json['open']),
      dayHigh: StockSearchItem._toDouble(json['dayHigh']),
      dayLow: StockSearchItem._toDouble(json['dayLow']),
      previousClose: StockSearchItem._toDouble(json['previousClose']),
      volume: StockSearchItem._toDouble(json['volume']),
    );
  }
}
