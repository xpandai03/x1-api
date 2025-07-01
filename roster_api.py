from flask import Flask, request, jsonify
from x1playwrightagent import scrape_roster

app = Flask(__name__)

@app.route("/")
def home():
    return "X1 Sports Roster API is running! Use /scrape_roster with base_url, sport, gender."

@app.route('/scrape_roster', methods=['GET'])
def scrape_roster_endpoint():
    try:
        base_url = request.args.get('base_url')
        sport = request.args.get('sport')
        gender = request.args.get('gender')

        # Input validation
        if not base_url or not sport or not gender:
            return jsonify({"error": "Missing required parameters: base_url, sport, gender"}), 400

        results = scrape_roster(base_url, sport, gender)
        return jsonify({
            "school": base_url,
            "sport": sport,
            "gender": gender,
            "roster": results
        })

    except Exception as e:
        import traceback
        print("API error:", traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/scrape_player', methods=['GET'])
def health_check():
    try:
        player_url = request.args.get('player_url')

        # Input validation
        if not player_url:
            return jsonify({"error": "Missing required parameter: player_url"}), 400

        from x1playwrightagent import extract_player_profile_html
        results = extract_player_profile_html(player_url)
        return jsonify({
            "player_url": player_url,
            "profile_html": results
        })

    except Exception as e:
        import traceback
        print("API error:", traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)