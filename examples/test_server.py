from flask import Flask, request

app = Flask(__name__)

@app.route('/logs', methods=['POST'])
def receive_logs():
    data = request.json
    print(f"\n{'='*50}")
    print(f"[{data.get('level')}] {data.get('service')}")
    print(f"Message: {data.get('message')}")
    print(f"File: {data.get('file')}:{data.get('line')}")
    print(f"Function: {data.get('func')}")
    print(f"Timestamp: {data.get('timestamp')}")
    print(f"{'='*50}")
    return {"status": "received"}, 200

if __name__ == '__main__':
    print("Log server listening on http://localhost:5000/logs")
    app.run(port=5000, debug=True)
