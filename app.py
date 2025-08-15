import os
import datetime
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from db import db
from models import BacktestResult
from backtest import run_backtest

# Create Flask app, set dist folder for React as static
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "dist"),
    static_url_path=""
)
app.config.from_object(Config)
db.init_app(app)
CORS(app)

# -------------------- API ROUTES --------------------

@app.route("/api/run_backtest", methods=["POST"])
def api_run_backtest():
    try:
        data = request.get_json()
        required_fields = ["ticker", "indicator", "normalisation", "start_date", "end_date"]
        if not data or not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields."}), 400

        ticker = data.get("ticker")
        indicator = data.get("indicator")
        normalisation = data.get("normalisation")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        result = run_backtest(ticker, indicator, normalisation, start_date, end_date)

        # Validate required keys
        required_keys = ["cagr", "sharpe", "max_drawdown", "win_rate", "equity_curve"]
        for k in required_keys:
            if k not in result:
                return jsonify({"error": f"Missing key in result: {k}"}), 500

        # Save to DB
        try:
            equity_curve_json = json.dumps(result["equity_curve"])
            backtest = BacktestResult(
                ticker=ticker,
                indicator=indicator,
                normalisation=normalisation,
                start_date=datetime.datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.datetime.strptime(end_date, "%Y-%m-%d"),
                cagr=result["cagr"],
                sharpe=result["sharpe"],
                max_drawdown=result["max_drawdown"],
                win_rate=result["win_rate"],
                equity_curve=equity_curve_json
            )
            db.session.add(backtest)
            db.session.commit()
        except Exception as db_error:
            print(f"DB save error: {db_error}")
            return jsonify({"error": "Internal server error saving result."}), 500

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_past_runs", methods=["GET"])
def api_get_past_runs():
    try:
        runs = BacktestResult.query.order_by(BacktestResult.created_at.desc()).limit(50).all()
        output = []
        for run in runs:
            output.append({
                "id": run.id,
                "ticker": run.ticker,
                "indicator": run.indicator,
                "normalisation": run.normalisation,
                "start_date": run.start_date.strftime("%Y-%m-%d") if run.start_date else None,
                "end_date": run.end_date.strftime("%Y-%m-%d") if run.end_date else None,
                "cagr": run.cagr,
                "sharpe": run.sharpe,
                "max_drawdown": run.max_drawdown,
                "win_rate": run.win_rate,
                "equity_curve": json.loads(run.equity_curve) if run.equity_curve else [],
                "created_at": run.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(run, "created_at") and run.created_at else None
            })
        return jsonify(output)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- FRONTEND ROUTES --------------------

@app.route("/")
def serve_react():
    return send_from_directory(app.static_folder, "index.html")

# Serve React for any route not starting with /api/
@app.errorhandler(404)
def not_found(e):
    path = request.path
    if path.startswith("/api/"):
        return jsonify({"error": "Not Found"}), 404
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True)
