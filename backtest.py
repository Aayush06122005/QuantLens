import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

# ---------------- FETCHING DATA ----------------
def fetch_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date, group_by='ticker')

    # If MultiIndex columns, flatten them
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[1] for col in data.columns]
    return data

# ---------------- INDICATOR CALCULATIONS ----------------
def calculate_rsi(close_series, period=14):
    """
    close_series: Pandas Series of close prices
    """
    close_series = pd.Series(close_series).astype(float)
    print(close_series)  # Debugging line to check the first few values
    return RSIIndicator(close=close_series, window=period).rsi()

# ---------------- NORMALISATION METHODS ----------------
def z_score(series):
    return (series - series.mean()) / series.std()

def min_max(series):
    return (series - series.min()) / (series.max() - series.min())

def mean_scaling(series):
    return series / series.mean()

def rank_scaling(series):
    return series.rank(pct=True)

# ---------------- METRICS CALCULATION ----------------
def calculate_metrics(equity_curve):
    returns = equity_curve.pct_change().dropna()

    start_val = equity_curve.iloc[0]
    end_val = equity_curve.iloc[-1]
    cagr = (end_val / start_val) ** (252 / len(equity_curve)) - 1

    sharpe = np.sqrt(252) * returns.mean() / returns.std() if returns.std() != 0 else 0
    max_drawdown = ((equity_curve - equity_curve.cummax()) / equity_curve.cummax()).min()
    win_rate = (returns > 0).mean() * 100

    return {
        'cagr': round(cagr * 100, 2),
        'sharpe': round(sharpe, 2),
        'max_drawdown': round(max_drawdown * 100, 2),
        'win_rate': round(win_rate, 2)
    }

# ---------------- BACKTEST ----------------
def run_backtest(ticker, indicator, normalisation, start_date, end_date, buy_threshold=30, sell_threshold=70):
    print(f"Fetching data for {ticker} from {start_date} to {end_date}")
    data = fetch_data(ticker, start_date, end_date)
    print(f"Data shape: {data.shape}")
    print(f"Columns: {data.columns.tolist()}")

    if 'Close' not in data.columns:
        raise ValueError("No 'Close' column found in data")

    # ---- Indicator ----
    if indicator == 'RSI':
        ind = calculate_rsi(data["Close"], period=14)
        print(f"RSI calculated, first 5 values: {ind.tail().tolist()}")
    else:
        raise NotImplementedError("Only RSI implemented")

    # ---- Normalisation ----
    if normalisation == 'Z-score':
        norm_ind = z_score(ind)
    elif normalisation == 'Min-Max':
        norm_ind = min_max(ind)
    elif normalisation == 'Mean Scaling':
        norm_ind = mean_scaling(ind)
    elif normalisation == 'Rank Scaling':
        norm_ind = rank_scaling(ind)
    else:
        norm_ind = ind

    print(f"Normalisation ({normalisation}) applied, first 5 values: {norm_ind.tail().tolist()}")

    # ---- Prepare DataFrame ----
    data['indicator'] = norm_ind
    data = data.dropna()
    print(f"Data after dropna shape: {data.shape}")

    # ---- Trading Logic ----
    position = 0
    equity = [100000]  # Starting capital
    buy_price = None

    for i in range(1, len(data)):
        indicator_value = float(data['indicator'].iloc[i])
        close_price = float(data['Close'].iloc[i])
        
        if position == 0 and indicator_value < float(buy_threshold):
            position = 1
            buy_price = close_price
        elif position == 1 and indicator_value > float(sell_threshold):
            position = 0
            sell_price = close_price
            equity.append(equity[-1] * (sell_price / buy_price))
        else:
            # If holding a position, update equity based on daily returns
            if position == 1:
                equity.append(equity[-1] * (close_price / data['Close'].iloc[i-1]))
            else:
                equity.append(equity[-1])


    equity_curve = pd.Series(equity, index=data.index[:len(equity)])

    # ---- Metrics ----
    metrics = calculate_metrics(equity_curve)
    print(f"Metrics: {metrics}")

    return {
        **metrics,
        'equity_curve': equity_curve.tolist(),
        'indicator_values': data['indicator'].tolist()
    }
