import 'package:flutter/material.dart';
import 'package:stock_frontend/services/service.dart';

// --- Colors ---
const Color tossBlue = Color(0xFF3182F6);
const Color tossBg = Color(0xFFF2F4F6);
const Color tossText = Color(0xFF191F28);
const Color tossSubtext = Color(0xFF8B95A1);

void main() {
  runApp(const FinTossApp());
}

class FinTossApp extends StatelessWidget {
  const FinTossApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FinToss AI',
      theme: ThemeData(
        fontFamily: 'Inter',
        scaffoldBackgroundColor: tossBg,
        primaryColor: tossBlue,
        useMaterial3: true,
      ),
      home: const MainScreen(),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Stockky',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.auto_awesome),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('AI chat is coming soon.')),
                      );
                    },
                  ),
                ],
              ),
            ),
            Expanded(
              child: _selectedIndex == 0
                  ? const HomeScreen()
                  : const Placeholder(),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (i) => setState(() => _selectedIndex = i),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.menu), label: 'All'),
        ],
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;
  String _query = '';
  String? _error;
  List<StockSearchItem> _results = const [];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final q = _controller.text.trim();
    setState(() {
      _query = q;
      _error = null;
      if (q.isEmpty) {
        _results = const [];
      }
    });

    if (q.isEmpty) {
      return;
    }

    setState(() => _isLoading = true);
    try {
      final fetched = await ApiService.searchStocks(q, limit: 30);
      if (!mounted) return;
      setState(() {
        _results = fetched;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _results = const [];
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
      children: [
        const _BalanceCard(),
        const SizedBox(height: 16),
        const _SectionTitle('Ticker Search'),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                onSubmitted: (_) => _search(),
                textCapitalization: TextCapitalization.characters,
                decoration: InputDecoration(
                  hintText: '예: AAPL, TSLA, NVDA',
                  prefixIcon: const Icon(Icons.search),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: _isLoading ? null : _search,
              child: const Text('검색'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (_query.isEmpty)
          const Text(
            '티커를 검색하면 모든 종목에서 일치 결과를 보여줍니다.',
            style: TextStyle(color: tossSubtext),
          ),
        if (_isLoading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Center(child: CircularProgressIndicator()),
          ),
        if (!_isLoading && _error != null)
          Text(
            '검색 실패: $_error',
            style: const TextStyle(color: Colors.red),
          ),
        if (!_isLoading && _error == null && _query.isNotEmpty && _results.isEmpty)
          const Text(
            '검색 결과가 없습니다.',
            style: TextStyle(color: tossSubtext),
          ),
        ..._results.map(
          (stock) => _ActivityTile(
            title: stock.name.isEmpty ? stock.symbol : stock.name,
            subtitle: stock.symbol,
            price: _formatPrice(stock.price),
            value: _formatChange(stock.changePercentage),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => StockDetailScreen(
                    symbol: stock.symbol,
                    fallbackName: stock.name.isEmpty ? stock.symbol : stock.name,
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  String _formatPrice(double? value) {
    if (value == null) {
      return '-';
    }
    return '\$${value.toStringAsFixed(2)}';
  }

  String _formatChange(double? value) {
    if (value == null) {
      return '-';
    }
    final sign = value > 0 ? '+' : '';
    return '$sign${value.toStringAsFixed(2)}%';
  }
}

class _BalanceCard extends StatelessWidget {
  const _BalanceCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Total Assets', style: TextStyle(color: tossSubtext)),
          SizedBox(height: 8),
          Text(
            '\$14,280.20',
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: tossText,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title);

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: tossText,
      ),
    );
  }
}

class StockDetailScreen extends StatefulWidget {
  const StockDetailScreen({
    super.key,
    required this.symbol,
    required this.fallbackName,
  });

  final String symbol;
  final String fallbackName;

  @override
  State<StockDetailScreen> createState() => _StockDetailScreenState();
}

class _StockDetailScreenState extends State<StockDetailScreen> {
  late Future<StockDetailItem> _future;

  @override
  void initState() {
    super.initState();
    _future = ApiService.fetchStockDetail(widget.symbol);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.symbol)),
      body: FutureBuilder<StockDetailItem>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '상세 조회 실패: ${snapshot.error}',
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: () {
                        setState(() {
                          _future = ApiService.fetchStockDetail(widget.symbol);
                        });
                      },
                      child: const Text('다시 시도'),
                    ),
                  ],
                ),
              ),
            );
          }

          final stock = snapshot.data;
          if (stock == null) {
            return const Center(
              child: Text('데이터가 없습니다.', style: TextStyle(color: tossSubtext)),
            );
          }

          final displayName = stock.name.isEmpty ? widget.fallbackName : stock.name;
          final changeText = _formatPercent(stock.changePercentage);
          final positive = stock.changePercentage != null && stock.changePercentage! >= 0;

          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Text(
                displayName,
                style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                  color: tossText,
                ),
              ),
              const SizedBox(height: 4),
              Text(stock.symbol, style: const TextStyle(color: tossSubtext)),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _formatCurrency(stock.price),
                      style: const TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.w700,
                        color: tossText,
                      ),
                    ),
                    Text(
                      changeText,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: changeText == '-'
                            ? tossSubtext
                            : (positive ? Colors.green : Colors.red),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              _DetailRow(label: '시가', value: _formatCurrency(stock.open)),
              _DetailRow(label: '고가', value: _formatCurrency(stock.dayHigh)),
              _DetailRow(label: '저가', value: _formatCurrency(stock.dayLow)),
              _DetailRow(label: '전일 종가', value: _formatCurrency(stock.previousClose)),
              _DetailRow(label: '거래량', value: _formatNumber(stock.volume)),
            ],
          );
        },
      ),
    );
  }

  String _formatCurrency(double? value) {
    if (value == null) return '-';
    return '\$${value.toStringAsFixed(2)}';
    }

  String _formatPercent(double? value) {
    if (value == null) return '-';
    final sign = value > 0 ? '+' : '';
    return '$sign${value.toStringAsFixed(2)}%';
  }

  String _formatNumber(double? value) {
    if (value == null) return '-';
    final rounded = value.round().toString();
    final chars = rounded.split('');
    final out = <String>[];
    for (var i = 0; i < chars.length; i++) {
      final reverseIndex = chars.length - i;
      out.add(chars[i]);
      if (reverseIndex > 1 && reverseIndex % 3 == 1) {
        out.add(',');
      }
    }
    return out.join();
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: tossSubtext)),
          Text(
            value,
            style: const TextStyle(
              color: tossText,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActivityTile extends StatelessWidget {
  const _ActivityTile({
    required this.title,
    required this.subtitle,
    required this.price,
    required this.value,
    this.onTap,
  });

  final String title;
  final String subtitle;
  final String price;
  final String value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isPositive = value.startsWith('+');

    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: ListTile(
        onTap: onTap,
        title: Text(
          title,
          style: const TextStyle(color: tossText, fontWeight: FontWeight.w600),
        ),
        subtitle: Text(subtitle, style: const TextStyle(color: tossSubtext)),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              price,
              style: const TextStyle(
                color: tossText,
                fontWeight: FontWeight.w700,
              ),
            ),
            Text(
              value,
              style: TextStyle(
                color: value == '-' ? tossSubtext : (isPositive ? Colors.green : Colors.red),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
