import 'package:flutter/material.dart';
import 'package:phishing/login.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:io';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  ThemeMode _themeMode = ThemeMode.system;

  void _toggleThemeMode() {
    setState(() {
      _themeMode = _themeMode == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        brightness: Brightness.light,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: _themeMode,
      home: AnalyzePage(onToggleTheme: _toggleThemeMode),
    );
  }
}

class AnalyzePage extends StatefulWidget {
  final VoidCallback onToggleTheme;

  const AnalyzePage({super.key, required this.onToggleTheme});

  @override
  State<AnalyzePage> createState() => _AnalyzePageState();
}

class _AnalyzePageState extends State<AnalyzePage> {
  final FocusNode _textFieldFocusNode = FocusNode();
  final TextEditingController _searchController = TextEditingController();
  final List<Map<String, String>> _messages = [
    {
      'message': 'Note: This analyzer helps detect potential phishing URLs or Malware by assessing various security factors. '
          'Please enter a URL/MSG for analysis to proceed.',
      'side': 'left'
    }
  ];
  bool _loading = false;
  bool _isTextFieldEnabled = false;
  String _selectedOption = 'URL';
  List<String> historyItems = [];

  @override
  void initState() {
    super.initState();
    _fetchSearchHistory();
  }

  // Analyze History in Drawer
  Future<void> _fetchSearchHistory() async {
    try {
      final response = await http.get(Uri.parse('http://10.0.2.2:5000/search_history?AccountID=$loggedInAccountID'));
      print('Response Status: ${response.statusCode}');
      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        if (data['success'] == true) {
          final List<dynamic> histories = data['histories'];
          setState(() {
            historyItems = histories.map<String>((item) => item['analysisContent'] as String).toList();
          });
        } else {
          throw Exception('Failed to load search history');
        }
      } else {
        throw Exception('Failed to load search history');
      }
    } catch (error) {
      print('Error fetching search history: $error');
    }
  }
  Widget buildHistoryList() {
    return ListView(
      children: historyItems.map<Widget>((item) {
        String truncatedContent = item;
        if (truncatedContent.length > 30) {
          truncatedContent = truncatedContent.substring(0, 30) + '...';  // Truncate to 30 chars
        }
        Icon leadingIcon;
        switch (item) {
          case 'URL':
            leadingIcon = Icon(Icons.link);
            break;
          case 'MSG':
            leadingIcon = Icon(Icons.message);
            break;
          case 'FILE':
            leadingIcon = Icon(Icons.file_copy);
            break;
          default:
            leadingIcon = Icon(Icons.link);
            break;
        }
        return ListTile(
          leading: leadingIcon,
          title: Text(truncatedContent),
        );
      }).toList(),
    );
  }

  @override
  void dispose() {
    _textFieldFocusNode.dispose();
    _searchController.dispose();
    super.dispose();
  }

  // Basic Controller
  void _navigateToLogin(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => LoginPage()),
    );
  }
  void _handleHeaderTap(BuildContext context) {
    if (loggedInUserName == '') {
      _navigateToLogin(context);
    } else {
      showDialog(
        context: context,
        builder: (BuildContext context) {
          return AlertDialog(
            title: const Text("Tips"),
            content: const Text("Are you sure you want to log out?"),
            actions: <Widget>[
              TextButton(
                child: const Text("Yes"),
                onPressed: () {
                  setState(() {
                    loggedInUserName = '';
                  });
                  Navigator.of(context).pop();
                  },
              ),
              TextButton(
                child: const Text("No"),
                onPressed: () {
                  Navigator.of(context).pop();
                },
              ),
            ],
          );
        },
      );
    }
  }

  // Search Button Function
  Future<void> _performSearch() async {
    FocusScope.of(context).unfocus();

    final input = _searchController.text.trim();
    if (input.isEmpty) {
      _addMessage('Please enter a value to search.', 'left');
      return;
    }

    setState(() {
      _loading = true;
      _messages.removeWhere((msg) => msg['side'] == 'left');
      _addMessage('Analyzing input...', 'left');
    });

    String apiUrl;
    Map<String, String> body = {};

    switch (_selectedOption) {
      case 'URL':
        apiUrl = 'http://10.0.2.2:5000/url_analyze';
        body = {'url': input};
        break;
      case 'MSG':
        apiUrl = 'http://10.0.2.2:5000/msg_analyze';
        body = {'msg': input};
        break;
      default:
        apiUrl = 'http://10.0.2.2:5000/url_analyze';
        body = {'url': input};
    }

    try {
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      setState(() {
        _loading = false;
        if (response.statusCode == 200 && _selectedOption == 'URL') {
          final result = jsonDecode(response.body);
          String isPhishing = result['is_phishing'] == true ? 'Yes' : 'No';
          String confidence = result['confidence_score']?.toString() ?? 'N/A';
          String fullResult = const JsonEncoder.withIndent('  ').convert(result);

          _addMessage('Is Phishing: $isPhishing', 'left');
          _addMessage('Confidence: $confidence', 'left');
          _addMessage('Full Result: $fullResult', 'left');
        } else if (response.statusCode == 200 && _selectedOption == 'MSG') {
          final result = jsonDecode(response.body);
          String fullResult = result['analysis'];
          _addMessage(fullResult, 'left');
        } else {
          _addMessage('Error occurred: ${response.statusCode}', 'left');
        }
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _addMessage('Error occurred: $e', 'left');
      });
    }
  }

  // Chat Part/Report Part
  void _addMessage(String message, String side) {
    setState(() {
      _messages.add({'message': message, 'side': side});
    });
  }
  Widget _buildChatBubble(String message, String side) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final bubbleColor = side == 'left'
        ? (isDarkMode ? Colors.grey[800] : Colors.grey[300])
        : (isDarkMode ? Colors.blue[600] : Colors.blue[300]);
    final textColor = isDarkMode ? Colors.white : Colors.black;

    return Align(
      alignment: side == 'left' ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 5, horizontal: 10),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: bubbleColor,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          message,
          style: TextStyle(fontSize: 16, color: textColor),
        ),
      ),
    );
  }
  void _onOptionSelected(String option) {
    setState(() {
      _selectedOption = option;
    });
  }

  // File Analysis Part
  Future<void> _pickFileAndAnalyze() async {
    final result = await FilePicker.platform.pickFiles();
    if (result != null) {
      final file = result.files.single;
      final filePath = file.path;
      if (filePath == null) {
        setState(() {
          _loading = false;
          _addMessage('Error: No file path found', 'left');
        });
        return;
      }

      setState(() {
        _loading = true;
        _messages.removeWhere((msg) => msg['side'] == 'left');
        _addMessage('Uploading file for analysis...', 'left');
      });

      try {
        final analysis = await _uploadFileToVirusTotal(filePath);

        setState(() {
          _loading = false;
          _addMessage('Is Malicious: ${analysis['isMalicious']}', 'left');
          _addMessage('Confidence: ${analysis['confidence']}%', 'left');
          _addMessage('Full Result: ${analysis['fullResult']}', 'left');
        });
      } catch (e) {
        setState(() {
          _loading = false;
          _addMessage('Error occurred: $e', 'left');
        });
      }
    } else {
      setState(() {
        _loading = false;
        _addMessage('No file selected', 'left');
      });
    }
  }
  Future<Map<String, dynamic>> _uploadFileToVirusTotal(String filePath) async {
    const apiKey = '81b7d937b90ef73f872000212b878181f802ddbaba129ea843f5397a698660f8';
    final uploadUri = Uri.parse('https://www.virustotal.com/api/v3/files');

    final uploadRequest = http.MultipartRequest('POST', uploadUri)
      ..headers['x-apikey'] = apiKey
      ..files.add(await http.MultipartFile.fromPath('file', filePath));

    final uploadResponse = await uploadRequest.send();
    final uploadResponseBody = await http.Response.fromStream(uploadResponse);

    if (uploadResponse.statusCode == 200) {
      final uploadResult = jsonDecode(uploadResponseBody.body);

      if (uploadResult.containsKey('data') && uploadResult['data'].containsKey('id')) {
        final analysisId = uploadResult['data']['id'];
        return await _fetchAnalysisResults(analysisId, apiKey);
      } else {
        throw Exception('Error: Missing analysis ID in the upload response.');
      }
    } else {
      throw Exception('Error: ${uploadResponse.statusCode} - ${uploadResponseBody.body}');
    }
  }
  Future<Map<String, dynamic>> _fetchAnalysisResults(String analysisId, String apiKey) async {
    final analysisUri = Uri.parse('https://www.virustotal.com/api/v3/analyses/$analysisId');

    while (true) {
      final response = await http.get(analysisUri, headers: {'x-apikey': apiKey});
      final result = jsonDecode(response.body);

      if (response.statusCode == 200 && result.containsKey('data')) {
        final data = result['data'];

        if (data.containsKey('attributes') && data['attributes']['status'] == 'completed') {
          final attributes = data['attributes'];
          final stats = attributes['stats'];

          if (stats != null) {
            final maliciousCount = stats['malicious'] ?? 0;
            final suspiciousCount = stats['suspicious'] ?? 0;
            final harmlessCount = stats['harmless'] ?? 0;

            final totalCount = maliciousCount + suspiciousCount + harmlessCount;
            final confidence = totalCount > 0
                ? ((maliciousCount / totalCount) * 100).round()
                : 0;

            final isMalicious = maliciousCount > 0;

            return {
              'isMalicious': isMalicious,
              'confidence': confidence,
              'fullResult': '''
VirusTotal Analysis Results:
- Malicious: $maliciousCount
- Suspicious: $suspiciousCount
- Harmless: $harmlessCount
              
View detailed report: https://www.virustotal.com/gui/file/$analysisId
              '''
            };
          }
        }
      } else if (response.statusCode != 200) {
        throw Exception('Error fetching analysis results: ${response.statusCode} - ${response.body}');
      }
      await Future.delayed(const Duration(seconds: 5));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Suspicion Analyzer',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        centerTitle: true,
        leading: Builder(
          builder: (context) {
            return IconButton(
              icon: const Icon(Icons.menu),
              onPressed: () {
                FocusScope.of(context).unfocus();
                _textFieldFocusNode.unfocus();
                Scaffold.of(context).openDrawer();
              },
            );
          },
        ),
      ),
      extendBody: true,
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: const BoxDecoration(
                color: Colors.black,
              ),
              child: ListTile(
                leading: const Icon(
                  Icons.login,
                  color: Colors.white,
                ),
                title: Text(
                  loggedInUserName == '' ? 'Login' : 'Welcome',
                  style: const TextStyle(color: Colors.white),
                ),
                onTap: () => _handleHeaderTap(context),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.brightness_6),
              title: const Text('Toggle Dark Mode'),
              onTap: widget.onToggleTheme,
            ),
            const ListTile(
              leading: Icon(Icons.history),
              title: Text('Analyze History'),
            ),
            ...historyItems.map((item) {
              return ListTile(
                leading: const Icon(Icons.history),
                title: Text(item),
              );
            }).toList(),
          ],
        ),
      ),
      body: GestureDetector(
        onTap: () {
          FocusScope.of(context).unfocus();
          setState(() {
            _isTextFieldEnabled = false;
          });
        },
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: ListView.builder(
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      return _buildChatBubble(message['message']!, message['side']!);
                    },
                  ),
                ),
                Row(
                  children: [
                    PopupMenuButton<String>(
                      icon: const Icon(Icons.expand_more),
                      onSelected: (option) {
                        if (option == 'FILE') {
                          _pickFileAndAnalyze();
                        } else {
                          _onOptionSelected(option);
                        }
                      },
                      itemBuilder: (context) => [
                        const PopupMenuItem(value: 'URL', child: Text('URL')),
                        const PopupMenuItem(value: 'MSG', child: Text('MSG')),
                        const PopupMenuItem(value: 'FILE', child: Text('FILE')),
                      ],
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          setState(() {
                            _isTextFieldEnabled = true;
                          });
                          _textFieldFocusNode.requestFocus();
                        },
                        child: AbsorbPointer(
                          absorbing: !_isTextFieldEnabled,
                          child: TextField(
                            controller: _searchController,
                            focusNode: _textFieldFocusNode,
                            decoration: const InputDecoration(
                              hintText: 'Enter URL or message...',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    IconButton(
                      icon: _loading
                          ? const CircularProgressIndicator()
                          : const Icon(Icons.search),
                      onPressed: _loading ? null : _performSearch,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
