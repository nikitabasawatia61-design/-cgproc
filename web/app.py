import sys
from datetime import date
from pathlib import Path

from flask import Flask, render_template, request, jsonify

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import database as db

app = Flask(__name__)


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    new_only = request.args.get("new", "") == "1"
    tenders = db.get_all_tenders(search=search or None, new_only=new_only)
    stats = db.get_stats()
    return render_template(
        "index.html",
        tenders=tenders,
        stats=stats,
        search=search,
        new_only=new_only,
        today=date.today().isoformat(),
    )


@app.route("/api/tenders")
def api_tenders():
    search = request.args.get("q", "").strip()
    new_only = request.args.get("new", "") == "1"
    tenders = db.get_all_tenders(search=search or None, new_only=new_only)
    return jsonify(tenders)


@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_stats())


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
