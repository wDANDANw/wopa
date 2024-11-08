import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

String loggedInUserName = '';

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
      home: UploadPage(onToggleTheme: _toggleThemeMode),
    );
  }
}

class UploadPage extends StatefulWidget {
  final VoidCallback onToggleTheme;

  const UploadPage({super.key, required this.onToggleTheme});

  @override
  State<UploadPage> createState() => _UploadPageState();
}

class _UploadPageState extends State<UploadPage> {
  final FocusNode _textFieldFocusNode = FocusNode();

  @override
  void dispose() {
    _textFieldFocusNode.dispose();
    super.dispose();
  }

  void _navigateToLogin(BuildContext context) {
    // Your logic to navigate to the login page
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => LoginPage()),
    );
  }

  void _handleHeaderTap(BuildContext context) {
    if (loggedInUserName == '') {
      // If not logged in, navigate to login page
      _navigateToLogin(context);
    } else {
      // If logged in, log out by setting the username to null
      setState(() {
        loggedInUserName = ''; // Clear the username on logout
      });
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
                  loggedInUserName ==''? 'Login':'Welcome',
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
          ],
        ),
      ),
      body: UrlUpload(focusNode: _textFieldFocusNode),
    );
  }
}

class UrlUpload extends StatefulWidget {
  final FocusNode focusNode;

  const UrlUpload({super.key, required this.focusNode});

  @override
  _UrlUploadState createState() => _UrlUploadState();
}

class _UrlUploadState extends State<UrlUpload> {
  final TextEditingController _searchController = TextEditingController();
  final List<Map<String, String>> _messages = [
    {
      'message': 'Note: This analyzer helps detect potential phishing URLs by assessing various security factors. '
          'Please enter a URL for analysis to proceed.',
      'side': 'left'
    }
  ];
  bool _loading = false;
  bool _isTextFieldEnabled = false; // Track if the TextField is enabled

  Future<void> _performSearch() async {
    FocusScope.of(context).unfocus();

    final url = _searchController.text;
    if (url.isEmpty) {
      _addMessage('Please enter a URL to search.', 'left');
      return;
    }

    setState(() {
      _loading = true;
      _messages.clear(); // Clear initial note
      _addMessage('Analyzing URL...', 'left');
    });

    final apiUrl = 'http://10.0.2.2:5000/analyze';
    final response = await http.post(
      Uri.parse(apiUrl),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'url': url}),
    );

    setState(() {
      _loading = false;
      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);
        String isPhishing = result['is_phishing'] != null
            ? (result['is_phishing'] ? 'Yes' : 'No')
            : 'N/A';
        String confidence = result['confidence_score']?.toString() ?? 'N/A';
        String fullResult = const JsonEncoder.withIndent('  ').convert(result);

        _addMessage('Is Phishing: $isPhishing', 'left');
        _addMessage('Confidence: $confidence', 'left');
        _addMessage('Full Result: $fullResult', 'left');
      } else {
        _addMessage('Error occurred: ${response.statusCode}', 'left');
      }
    });
  }

  void _addMessage(String message, String side) {
    setState(() {
      _messages.add({'message': message, 'side': side});
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: GestureDetector(
        onTap: () {
          FocusScope.of(context).unfocus(); // Unfocus when tapping outside
          setState(() {
            _isTextFieldEnabled = false; // Make the TextField read-only again
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
                      return _buildChatBubble(
                        _messages[index]['message']!,
                        _messages[index]['side']!,
                      );
                    },
                  ),
                ),
                Row(
                  children: [
                    PopupMenuButton<String>(
                      icon: const Icon(Icons.expand_more),
                      onSelected: (value) {
                        FocusScope.of(context).unfocus(); // Unfocus when a menu item is selected
                      },
                      itemBuilder: (BuildContext context) {
                        return [
                          const PopupMenuItem<String>(
                            value: 'URL',
                            child: Text('URL'),
                          ),
                          const PopupMenuItem<String>(
                            value: 'MSG',
                            child: Text('MSG'),
                          ),
                          const PopupMenuItem<String>(
                            value: 'FILE',
                            child: Text('FILE'),
                          ),
                        ];
                      },
                    ),
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          // Enable the TextField when clicked
                          setState(() {
                            _isTextFieldEnabled = true; // Enable the TextField
                          });
                          widget.focusNode.requestFocus(); // Request focus
                        },
                        child: AbsorbPointer(
                          absorbing: !_isTextFieldEnabled, // Absorb taps if not enabled
                          child: TextField(
                            controller: _searchController,
                            focusNode: widget.focusNode,
                            enabled: _isTextFieldEnabled, // Control the enabled state
                            decoration: InputDecoration(
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12.0),
                                borderSide: const BorderSide(color: Colors.black),
                              ),
                              filled: true,
                              fillColor: Theme.of(context).brightness == Brightness.dark
                                  ? Colors.black
                                  : Colors.white,
                            ),
                            onTap: () {
                              // Allow typing when tapped
                              setState(() {
                                _isTextFieldEnabled = true;
                              });
                            },
                            onEditingComplete: () {
                              // Disable the TextField when editing is complete
                              setState(() {
                                _isTextFieldEnabled = false;
                              });
                              FocusScope.of(context).unfocus(); // Unfocus on editing complete
                            },
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white10,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12.0),
                        ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 12,
                        ),
                      ),
                      onPressed: _performSearch,
                      child: Text(
                        'Analyze',
                        style: TextStyle(
                          fontSize: 18,
                          color: Theme.of(context).brightness == Brightness.dark
                              ? Colors.white
                              : Colors.black,
                        ),
                      ),
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

  Widget _buildChatBubble(String message, String side) {
    final alignment = side == 'left' ? CrossAxisAlignment.start : CrossAxisAlignment.end;
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
}

class Report {
  final String isPhishing;
  final String confidence;
  final String fullResult;

  Report({
    required this.isPhishing,
    required this.confidence,
    required this.fullResult,
  });

  String reportBrief() {
    return 'Is Phishing: $isPhishing\nConfidence: $confidence';
  }

  String reportFull() {
    return fullResult;
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  void _login() {
    if (_formKey.currentState?.validate() ?? false) {
      setState(() {
        _isLoading = true;
      });

      Future.delayed(const Duration(seconds: 1), () {
        setState(() {
          loggedInUserName = _usernameController.value.toString();
          _isLoading = false;
        });

        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => const MyApp()),
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Login'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextFormField(
                  controller: _usernameController,
                  decoration: const InputDecoration(
                    labelText: 'Username',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your username';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16.0),
                TextFormField(
                  controller: _passwordController,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                  ),
                  obscureText: true,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your password';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 20.0),
                _isLoading
                    ? const CircularProgressIndicator()
                    : ElevatedButton(
                  onPressed: _login,
                  child: const Text('Login'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
