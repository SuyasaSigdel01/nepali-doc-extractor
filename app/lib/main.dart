import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:audioplayers/audioplayers.dart';
import 'package:image_picker/image_picker.dart';

const apiBase = 'http://127.0.0.1:8000';

const _nepDigits = '०१२३४५६७८९';

String toNepaliDigits(String s) => s.split('').map((c) {
      final i = '0123456789'.indexOf(c);
      return i == -1 ? c : _nepDigits[i];
    }).join();

String formatAmount(num value, String lang) {
  final digits = value.round().toString();
  final buf = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buf.write(',');
    buf.write(digits[i]);
  }
  final out = buf.toString();
  return lang == 'ne' ? toNepaliDigits(out) : out;
}

String prettyLabel(String key) => key
    .split('_')
    .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
    .join(' ');

class ExtractResult {
  final Map<String, dynamic> fields;
  final Map<String, List<String>> explanations;
  final Map<String, String> audio;

  ExtractResult({
    required this.fields,
    required this.explanations,
    required this.audio,
  });

  factory ExtractResult.fromJson(Map<String, dynamic> j) => ExtractResult(
        fields: Map<String, dynamic>.from(j['fields'] as Map),
        explanations: (j['explanations'] as Map).map(
          (k, v) => MapEntry(
            k as String,
            (v as List).map((e) => e.toString()).toList(),
          ),
        ),
        audio: (j['audio'] as Map)
            .map((k, v) => MapEntry(k as String, v.toString())),
      );
}

void main() => runApp(const App());

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Bill Reader',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF0F6E56),
            brightness: Brightness.light,
          ),
        ),
        home: const HomePage(),
      );
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _player = AudioPlayer();

  bool _busy = false;
  String _lang = 'ne';
  String? _error;
  ExtractResult? _result;
  bool _playing = false;

  final _questionController = TextEditingController();
  String? _answer;
  bool _askBusy = false;

  @override
  void initState() {
    super.initState();
    _player.onPlayerStateChanged.listen((s) {
      if (mounted) setState(() => _playing = s == PlayerState.playing);
    });
  }

  @override
  void dispose() {
    _questionController.dispose();
    _player.dispose();
    super.dispose();
  }

  Future<void> _pickAndUpload(ImageSource source) async {
    final picked = await ImagePicker().pickImage(
      source: source,
      imageQuality: 90,
    );
    if (picked == null) return;

    await _player.stop();
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
      _answer = null;
    });

    try {
      final bytes = await picked.readAsBytes();
      final req = http.MultipartRequest('POST', Uri.parse('$apiBase/extract'))
        ..files.add(http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: picked.name,
        ));

      final res = await http.Response.fromStream(await req.send());
      final body = utf8.decode(res.bodyBytes);

      if (res.statusCode == 200) {
        setState(() => _result =
            ExtractResult.fromJson(jsonDecode(body) as Map<String, dynamic>));
      } else if (res.statusCode == 422) {
        setState(() => _error = _lang == 'ne'
            ? 'यो कागजात चिन्न सकिएन। अहिले खानेपानीको बिल मात्र पढ्न मिल्छ।'
            : "Couldn't read this document. Only water bills are supported so far.");
      } else {
        setState(() => _error = 'Server error ${res.statusCode}');
      }
    } catch (e) {
      setState(() => _error = _lang == 'ne'
          ? 'जडान हुन सकेन। सर्भर चलिरहेको छ कि जाँच्नुहोस्।'
          : 'Could not connect. Check the server is running.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _togglePlay() async {
    final url = _result?.audio[_lang];
    if (url == null) return;

    if (_playing) {
      await _player.pause();
    } else {
      await _player.play(UrlSource('$apiBase$url'));
    }
  }

  Future<void> _askQuestion() async {
    final q = _questionController.text.trim();
    if (q.isEmpty || _result == null) return;
    setState(() {
      _askBusy = true;
      _answer = null;
    });
    try {
      final res = await http.post(
        Uri.parse('$apiBase/ask'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'question': q,
          'fields': _result!.fields,
          'lang': _lang,
        }),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() => _answer = data['answer'] as String);
        await _player.play(UrlSource('$apiBase${data['audio']}'));
      }
    } catch (e) {
      setState(() => _answer = _lang == 'ne'
          ? 'जडान हुन सकेन।'
          : 'Could not connect.');
    } finally {
      if (mounted) setState(() => _askBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: Text(_lang == 'ne' ? 'बिल पढ्ने' : 'Bill Reader'),
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: SegmentedButton<String>(
              style: SegmentedButton.styleFrom(
                backgroundColor: scheme.primary,
                foregroundColor: scheme.onPrimary,
                selectedBackgroundColor: scheme.onPrimary,
                selectedForegroundColor: scheme.primary,
                side: BorderSide(color: scheme.onPrimary.withValues(alpha: 0.5)),
                visualDensity: VisualDensity.compact,
              ),
              segments: const [
                ButtonSegment(value: 'ne', label: Text('नेपाली')),
                ButtonSegment(value: 'en', label: Text('EN')),
              ],
              selected: {_lang},
              showSelectedIcon: false,
              onSelectionChanged: (s) async {
                await _player.stop();
                setState(() => _lang = s.first);
              },
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: _busy
            ? _buildBusy(scheme)
            : _result != null
                ? _buildResult(scheme)
                : _buildEmpty(scheme),
      ),
      floatingActionButton: _busy
          ? null
          : FloatingActionButton.extended(
              onPressed: () => _pickAndUpload(ImageSource.camera),
              icon: const Icon(Icons.photo_camera, size: 28),
              label: Text(
                _lang == 'ne' ? 'बिल खिच्नुहोस्' : 'Photograph bill',
                style: const TextStyle(fontSize: 16),
              ),
              backgroundColor: scheme.primary,
              foregroundColor: scheme.onPrimary,
            ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }

  Widget _buildBusy(ColorScheme scheme) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: scheme.primary),
            const SizedBox(height: 24),
            Text(
              _lang == 'ne' ? 'बिल पढ्दै...' : 'Reading the bill...',
              style: const TextStyle(fontSize: 18),
            ),
          ],
        ),
      );

  Widget _buildEmpty(ColorScheme scheme) => Center(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(32, 0, 32, 80),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.receipt_long_outlined,
                size: 96,
                color: scheme.primary.withValues(alpha: 0.35),
              ),
              const SizedBox(height: 28),
              Text(
                _lang == 'ne'
                    ? 'आफ्नो बिलको फोटो खिच्नुहोस्'
                    : 'Take a photo of your bill',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 12),
              Text(
                _lang == 'ne'
                    ? 'कति तिर्नुपर्ने हो भनेर बोलेर सुनाउँछ।'
                    : 'It will read out how much you owe.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: scheme.onSurfaceVariant),
              ),
              const SizedBox(height: 32),
              OutlinedButton.icon(
                onPressed: () => _pickAndUpload(ImageSource.gallery),
                icon: const Icon(Icons.image_outlined),
                label: Text(
                  _lang == 'ne' ? 'ग्यालरीबाट छान्नुहोस्' : 'Choose from gallery',
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 28),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: scheme.errorContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _error!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: scheme.onErrorContainer),
                  ),
                ),
              ],
            ],
          ),
        ),
      );

  Widget _buildResult(ColorScheme scheme) {
    final r = _result!;
    final payable = r.fields['payable_amount'];
    final subject = r.fields['subject'];
    final issuer = r.fields['issuer'];
    final lines = r.explanations[_lang] ?? const [];

    final detail = Map<String, dynamic>.from(r.fields)
      ..remove('document_type')
      ..remove('payable_amount');

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
      children: [
        if (payable is num)
          _hero(
            scheme,
            label: _lang == 'ne' ? 'तिर्नुपर्ने रकम' : 'Total payable',
            value: '${_lang == 'ne' ? 'रु ' : 'Rs '}'
                '${formatAmount(payable, _lang)}',
            valueSize: 46,
          )
        else if (subject is String && subject.isNotEmpty)
          _hero(
            scheme,
            label: issuer is String && issuer.isNotEmpty
                ? issuer
                : (_lang == 'ne' ? 'सूचना' : 'Notice'),
            value: subject,
            valueSize: 26,
          ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: r.audio[_lang] == null ? null : _togglePlay,
          icon: Icon(_playing ? Icons.pause : Icons.volume_up, size: 30),
          label: Text(
            _playing
                ? (_lang == 'ne' ? 'रोक्नुहोस्' : 'Pause')
                : (_lang == 'ne' ? 'सुन्नुहोस्' : 'Listen'),
            style: const TextStyle(fontSize: 19),
          ),
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(64),
            backgroundColor: scheme.secondaryContainer,
            foregroundColor: scheme.onSecondaryContainer,
          ),
        ),
        const SizedBox(height: 20),
        Card(
          elevation: 0,
          color: scheme.surfaceContainerHighest,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final line in lines)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      line,
                      style: const TextStyle(fontSize: 18, height: 1.5),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          elevation: 0,
          color: scheme.surfaceContainerHigh,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              shape: const Border(),
              title: Text(
                _lang == 'ne' ? 'सबै विवरण' : 'All details',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              ),
              children: [
                for (final e in detail.entries)
                  ListTile(
                    dense: true,
                    title: Text(prettyLabel(e.key)),
                    trailing: Text(
                      e.value == null
                          ? '—'
                          : e.value is num
                              ? formatAmount(e.value as num, _lang)
                              : e.value.toString(),
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          elevation: 0,
          color: scheme.surfaceContainerHighest,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _lang == 'ne' ? 'प्रश्न सोध्नुहोस्' : 'Ask a question',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _questionController,
                        decoration: InputDecoration(
                          hintText: _lang == 'ne'
                              ? 'जस्तै: कति तिर्नुपर्छ?'
                              : 'e.g. How much do I owe?',
                          border: const OutlineInputBorder(),
                          isDense: true,
                        ),
                        onSubmitted: (_) => _askQuestion(),
                      ),
                    ),
                    const SizedBox(width: 8),
                    _askBusy
                        ? const SizedBox(
                            width: 48,
                            height: 48,
                            child: Center(child: CircularProgressIndicator()),
                          )
                        : IconButton.filled(
                            onPressed: _askQuestion,
                            icon: const Icon(Icons.send),
                          ),
                  ],
                ),
                if (_answer != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _answer!,
                    style: const TextStyle(fontSize: 17, height: 1.5),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _hero(
    ColorScheme scheme, {
    required String label,
    required String value,
    required double valueSize,
  }) =>
      Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 20),
        decoration: BoxDecoration(
          color: scheme.primary,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          children: [
            Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16,
                color: scheme.onPrimary.withValues(alpha: 0.85),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              value,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: valueSize,
                fontWeight: FontWeight.w600,
                color: scheme.onPrimary,
              ),
            ),
          ],
        ),
      );
}