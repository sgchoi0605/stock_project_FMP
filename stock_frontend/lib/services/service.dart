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
}
