import json
import logging
from flask import Flask, request, jsonify
from groq import Groq
import pymysql
import pymysql.cursors


app = Flask(__name__)
client = Groq(api_key="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")


def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="123456",
        database="phishing"
    )


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'success': False, 'message': 'Invalid input'}), 400
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        query = "SELECT * FROM Accounts WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        if user:
            account_id = user['AccountID']
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'AccountID': account_id
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    except Exception as e:
        app.logger.error(f"Error in /login route: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/search_history', methods=['GET'])
def search_history():
    try:
        account_id = request.args.get('AccountID')
        if not account_id:
            return jsonify({'success': False, 'message': 'AccountID is required'}), 400
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        query = "SELECT * FROM Historys WHERE AccountID = %s"
        cursor.execute(query, (account_id,))
        histories = cursor.fetchall()
        if not histories:
            return jsonify({'success': False, 'message': 'No history records found for this AccountID'}), 404
        return jsonify({
            'success': True,
            'histories': histories
        })
    except pymysql.MySQLError as e:
        app.logger.error(f"MySQL Error: {str(e)}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/url_analyze', methods=['POST'])
def analyze_url_route():
    data = request.json
    url = data.get('url')
    analysis = analyze_url(url)
    return jsonify(analysis)


@app.route('/msg_analyze', methods=['POST'])
def analyze_msg_route():
    data = request.json
    msg = data.get('msg')
    analysis = analyze_msg(msg)
    return jsonify(analysis)


def analyze_url(url):
    prompt = f"""
    Analyze the following URL for phishing characteristics: {url}.
    Based on the analysis, provide the following structured JSON output:
    {{
      "is_phishing": (true/false),
      "confidence_score": (integer between 0-100),
      "indicators": [
        "list of specific reasons explaining why it's considered phishing or not"
      ]
    }}
    """
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192",
    )
    analysis = chat_completion.choices[0].message.content.strip()
    try:
        start_idx = analysis.index("{")
        end_idx = analysis.rindex("}") + 1
        json_part = analysis[start_idx:end_idx]
        analysis_json = json.loads(json_part)
    except (json.JSONDecodeError, ValueError):
        analysis_json = {"error": "Invalid JSON response", "raw_response": analysis}
    return analysis_json


logging.basicConfig(level=logging.DEBUG)


def analyze_msg(msg):
    logging.debug(f"Received msg: '{msg}'")
    if not msg or not isinstance(msg, str) or not msg.strip():
        logging.error("Invalid message. Message must be a non-empty string.")
        return {"error": "Invalid message. Message must be a non-empty string."}
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": msg}],
            model="llama3-8b-8192",
        )
        analysis = chat_completion.choices[0].message.content.strip()
        return {"analysis": analysis}
    except Exception as e:
        logging.error(f"Error while analyzing the message: {str(e)}")
        return {"error": f"Error while analyzing the message: {str(e)}"}


if __name__ == '__main__':
    app.run(port=5000)