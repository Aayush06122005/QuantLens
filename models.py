from db import db

class BacktestResult(db.Model):
    __tablename__ = "backtest_results"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticker = db.Column(db.String(10), nullable=False)
    indicator = db.Column(db.String(50), nullable=False)
    normalisation = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    cagr = db.Column(db.Float)
    sharpe = db.Column(db.Float)
    max_drawdown = db.Column(db.Float)
    win_rate = db.Column(db.Float)
    equity_curve = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
