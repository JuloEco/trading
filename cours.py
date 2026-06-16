import random
import time
from threading import Thread
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neon_news_trading_secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- BANQUE DE NEWS (Événements) ---
NEWS_POOL = [
    {"text": "🚀 NEON_TECH annonce une batterie quantique révolutionnaire ! Les investisseurs jubilent.", "ticker": "NNT", "bias": 4.5, "duration": 4},
    {"text": "🛡️ CYBER_SECURITY décroche le contrat de protection du serveur central de la Megacity.", "ticker": "CYBR", "bias": 2.5, "duration": 5},
    {"text": "🌌 MATRIX_CORP découvre une faille de duplication de crédits dans la Matrice. Spéculation maximale !", "ticker": "XMRX", "bias": 8.0, "duration": 3},
    {"text": "📈 Rumeurs de rachat de MATRIX_CORP par un conglomérat orbital. Le cours s'enflamme.", "ticker": "XMRX", "bias": 5.0, "duration": 4},
    {"text": "💥 Explosion d'un laboratoire de recherche chez NEON_TECH. Panique en bourse.", "ticker": "NNT", "bias": -5.0, "duration": 4},
    {"text": "👾 Un malware d'origine inconnue paralyse la moitié des clients de CYBER_SECURITY.", "ticker": "CYBR", "bias": -3.5, "duration": 5},
    {"text": "📉 Descente de la cyber-police dans les bureaux de MATRIX_CORP. Revente massive.", "ticker": "XMRX", "bias": -7.0, "duration": 3},
    {"text": "🛑 NEON_TECH visé par une enquête pour manipulation de l'IA de trading. Confiance en baisse.", "ticker": "NNT", "bias": -2.0, "duration": 4}
]

# --- ÉTAT DU JEU GLOBAL ---
game_state = {
    "stocks": {
        "NNT":  {"name": "NEON_TECH (NNT)", "price": 100.0, "history": [100.0], "labels": ["0s"], "volatility": (-1.5, 1.7), "active_bias": 0.0, "bias_countdown": 0, "last_change": 0.0},
        "CYBR": {"name": "CYBER_SECURITY (CYBR)", "price": 250.0, "history": [250.0], "labels": ["0s"], "volatility": (-0.8, 0.9), "active_bias": 0.0, "bias_countdown": 0, "last_change": 0.0},
        "XMRX": {"name": "MATRIX_CORP (XMRX)", "price": 45.0, "history": [45.0], "labels": ["0s"], "volatility": (-4.0, 4.5), "active_bias": 0.0, "bias_countdown": 0, "last_change": 0.0}
    },
    "player": {
        "cash": 1000.0,
        "shares": {"NNT": 0, "CYBR": 0, "XMRX": 0},
        "dividend_yield": 0.02,
        "fee": 1.00,
        "limit_orders": {
            "NNT": {"stop_loss": None, "take_profit": None},
            "CYBR": {"stop_loss": None, "take_profit": None},
            "XMRX": {"stop_loss": None, "take_profit": None}
        }
    },
    "competitors": {
        "Gordon_Gekko": {"name": "🕶️ Gordon Gekko AI", "cash": 1000.0, "shares": {"NNT": 0, "CYBR": 0, "XMRX": 0}},
        "Crypto_Whale": {"name": "🐋 Crypto Whale 99", "cash": 1000.0, "shares": {"NNT": 0, "CYBR": 0, "XMRX": 0}}
    },
    "current_news": "🌐 Bienvenue sur le Neon Trading Floor. Le marché est actuellement stable."
}

def get_net_worth():
    """ Calcule la valeur totale des actifs du joueur """
    total = game_state["player"]["cash"]
    for ticker, count in game_state["player"]["shares"].items():
        total += count * game_state["stocks"][ticker]["price"]
    return round(total, 2)

def get_leaderboard():
    """ Génère le classement ordonné par Valeur Nette """
    leaderboard = [{"name": "Vous (Trader)", "net_worth": get_net_worth()}]
    
    for comp_id, comp in game_state["competitors"].items():
        nw = comp["cash"]
        for ticker, count in comp["shares"].items():
            nw += count * game_state["stocks"][ticker]["price"]
        leaderboard.append({"name": comp["name"], "net_worth": round(nw, 2)})
        
    leaderboard.sort(key=lambda x: x["net_worth"], reverse=True)
    return leaderboard

def market_simulation():
    """ Boucle principale : gère le marché, les dividendes, les news, l'IA et les ordres automatiques """
    seconds = 0
    while True:
        time.sleep(1)
        seconds += 1
        
        # 1. Génération d'une News toutes les 30 secondes
        if seconds % 30 == 0:
            news = random.choice(NEWS_POOL)
            ticker = news["ticker"]
            game_state["stocks"][ticker]["active_bias"] = news["bias"]
            game_state["stocks"][ticker]["bias_countdown"] = news["duration"]
            game_state["current_news"] = news["text"]
            socketio.emit('news_flash', {'message': news["text"]})
        
        # 2. Mise à jour des cours toutes les 10 secondes
        if seconds % 10 == 0:
            for ticker, stock in game_state["stocks"].items():
                low, high = stock["volatility"]
                change_percent = random.uniform(low, high) + stock["active_bias"]
                
                if stock["bias_countdown"] > 0:
                    stock["bias_countdown"] -= 1
                    if stock["bias_countdown"] == 0:
                        stock["active_bias"] = 0.0
                
                new_price = round(stock["price"] * (1 + change_percent / 100), 2)
                stock["price"] = max(1.0, new_price)
                
                # FIX : On sauvegarde le taux propre à cette entreprise précise
                stock["last_change"] = round(change_percent, 2)
                
                stock["history"].append(stock["price"])
                stock["labels"].append(f"{seconds}s")
                
                if len(stock["history"]) > 30:
                    stock["history"].pop(0)
                    stock["labels"].pop(0)
            
            # --- ACTION DE L'IA (CONCURRENTS) ---
            for comp_id, comp in game_state["competitors"].items():
                t = random.choice(["NNT", "CYBR", "XMRX"])
                p = game_state["stocks"][t]["price"]
                
                if comp_id == "Gordon_Gekko" and t == "XMRX" and random.random() > 0.1: continue
                if comp_id == "Crypto_Whale" and t != "XMRX" and random.random() > 0.3: continue
                
                act = random.choice(["buy", "sell", "hold"])
                if act == "buy" and comp["cash"] >= (p + 1.0):
                    comp["cash"] = round(comp["cash"] - p - 1.0, 2)
                    comp["shares"][t] += 1
                elif act == "sell" and comp["shares"][t] > 0:
                    comp["shares"][t] -= 1
                    comp["cash"] = round(comp["cash"] + p - 1.0, 2)

            # --- SÉCURITÉ : VÉRIFICATION DES ORDRES LIMITES ---
            player = game_state["player"]
            triggered = False
            for ticker, stock in game_state["stocks"].items():
                orders = player["limit_orders"][ticker]
                shares = player["shares"][ticker]
                price = stock["price"]
                
                if shares > 0:
                    if orders["stop_loss"] is not None and price <= orders["stop_loss"]:
                        payout = round((price - player["fee"]) * shares, 2)
                        player["cash"] = round(player["cash"] + payout, 2)
                        player["shares"][ticker] = 0
                        orders["stop_loss"] = None
                        orders["take_profit"] = None
                        triggered = True
                        socketio.emit('notification', {'message': f"📉 STOP-LOSS DÉCLENCHÉ ! {shares} parts de {ticker} vendues automatiquement à {price}$ !"})
                    
                    elif orders["take_profit"] is not None and price >= orders["take_profit"]:
                        payout = round((price - player["fee"]) * shares, 2)
                        player["cash"] = round(player["cash"] + payout, 2)
                        player["shares"][ticker] = 0
                        orders["stop_loss"] = None
                        orders["take_profit"] = None
                        triggered = True
                        socketio.emit('notification', {'message': f"💰 TAKE-PROFIT DÉCLENCHÉ ! {shares} parts de {ticker} sécurisées à {price}$ !"})

            if triggered:
                player_data = player.copy()
                player_data["net_worth"] = get_net_worth()
                socketio.emit('player_update', player_data)

            # Envoi global de la mise à jour marché
            for ticker, stock in game_state["stocks"].items():
                socketio.emit('market_update', {
                    'ticker': ticker,
                    'price': stock["price"],
                    'history': stock["history"],
                    'labels': stock["labels"],
                    'change': stock["last_change"], # FIX : Utilise la valeur propre stockée
                    'net_worth': get_net_worth(),
                    'leaderboard': get_leaderboard()
                })
            
        # 3. Dividendes toutes les 2 minutes
        if seconds % 120 == 0:
            total_payout = 0.0
            player = game_state["player"]
            for t, count in player["shares"].items():
                if count > 0:
                    total_payout += count * game_state["stocks"][t]["price"] * player["dividend_yield"]
            
            if total_payout > 0:
                total_payout = round(total_payout, 2)
                player["cash"] = round(player["cash"] + total_payout, 2)
                
                player_data = player.copy()
                player_data["net_worth"] = get_net_worth()
                socketio.emit('player_update', player_data)
                socketio.emit('notification', {'message': f"💰 Dividendes reçus : +{total_payout}$ !"})

# --- LOGIQUE ROUTE FLASK ---



# --- LOGIQUE SOCKETIO ---

@socketio.on('buy_stock')
def handle_buy(data):
    ticker = data.get('ticker')
    if ticker not in game_state["stocks"]: return
    player = game_state["player"]
    price = game_state["stocks"][ticker]["price"]
    total_cost = price + player["fee"]
    
    if player["cash"] >= total_cost:
        player["cash"] = round(player["cash"] - total_cost, 2)
        player["shares"][ticker] += 1
        player_data = player.copy()
        player_data["net_worth"] = get_net_worth()
        emit('player_update', player_data, broadcast=True)
    else:
        emit('notification', {'message': f"❌ Fonds insuffisants ! (Prix: {price}$ + Taxe: {player['fee']}$)"}, room=False)

@socketio.on('sell_stock')
def handle_sell(data):
    ticker = data.get('ticker')
    if ticker not in game_state["stocks"]: return
    player = game_state["player"]
    price = game_state["stocks"][ticker]["price"]
    
    if player["shares"][ticker] > 0:
        player["shares"][ticker] -= 1
        player["cash"] = round(player["cash"] + price - player["fee"], 2)
        player_data = player.copy()
        player_data["net_worth"] = get_net_worth()
        emit('player_update', player_data, broadcast=True)
    else:
        emit('notification', {'message': "❌ Erreur : Aucune action à vendre !"}, room=False)

@socketio.on('set_limits')
def handle_set_limits(data):
    ticker = data.get('ticker')
    sl = data.get('sl')
    tp = data.get('tp')
    if ticker in game_state["stocks"]:
        orders = game_state["player"]["limit_orders"][ticker]
        orders["stop_loss"] = float(sl) if sl and sl != "" else None
        orders["take_profit"] = float(tp) if tp and tp != "" else None
        
        player_data = game_state["player"].copy()
        player_data["net_worth"] = get_net_worth()
        emit('player_update', player_data, broadcast=True)
        emit('notification', {'message': f"⚙️ Configuration Auto mise à jour ({ticker})"}, room=False)

@socketio.on('emergency_loan')
def handle_loan():
    player = game_state["player"]
    total_shares = sum(player["shares"].values())
    if player["cash"] < 5.0 and total_shares == 0:
        player["cash"] = 200.0
        player_data = player.copy()
        player_data["net_worth"] = get_net_worth()
        emit('player_update', player_data, broadcast=True)
        emit('notification', {'message': "💸 Prêt d'urgence octroyé : +200.00$"}, room=True)
    else:
        emit('notification', {'message': "🔒 Prêt refusé. Ressources encore disponibles !"}, room=False)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neon Trading Empire</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    
    <style>
        :root {
            --bg-color: #05060b;
            --card-bg: rgba(12, 14, 28, 0.8);
            --neon-cyan: #00f3ff;
            --neon-magenta: #ff0055;
            --neon-green: #00ff66;
            --text-color: #e2e8f0;
        }

        body {
            background-color: var(--bg-color); color: var(--text-color);
            font-family: 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0 0 40px 0;
            display: flex; flex-direction: column; align-items: center;
        }

        .news-ticker {
            width: 100%; background: rgba(20, 0, 40, 0.6); border-bottom: 2px solid var(--neon-magenta);
            box-shadow: 0 0 15px rgba(255, 0, 85, 0.2); padding: 10px 0; overflow: hidden; white-space: nowrap; margin-bottom: 25px;
        }
        .news-content {
            display: inline-block; padding-left: 100%; font-weight: bold; letter-spacing: 1px;
            color: #fff; text-shadow: 0 0 5px var(--neon-magenta); animation: marquee 25s linear infinite;
        }
        @keyframes marquee { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        h1 { font-size: 2.2rem; text-transform: uppercase; letter-spacing: 4px; color: #fff; text-shadow: 0 0 10px var(--neon-cyan); margin-bottom: 20px; }
        h3 { margin-top: 0; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 1px; }

        .game-container { display: flex; flex-direction: column; gap: 20px; width: 92%; max-width: 1050px; }

        .portfolio-panel {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;
            background: var(--card-bg); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px; padding: 15px 30px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        }
        .stat-box { text-align: center; }
        .stat-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; margin-bottom: 3px;}
        .stat-value { font-size: 1.7rem; font-weight: bold; }
        #p-networth { color: #fff; text-shadow: 0 0 10px var(--neon-cyan); }
        #p-cash { color: var(--neon-green); }

        .market-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .stock-card { background: var(--card-bg); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 12px; padding: 20px; cursor: pointer; transition: all 0.2s; }
        .stock-card.active { border-color: var(--neon-cyan); box-shadow: 0 0 15px rgba(0, 243, 255, 0.25); }
        .stock-card-header { display: flex; justify-content: space-between; align-items: center; }

        .main-layout-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        @media (max-width: 850px) { .main-layout-grid { grid-template-columns: 1fr; } }

        .main-panel { background: var(--card-bg); border: 1px solid rgba(0, 243, 255, 0.15); border-radius: 16px; padding: 25px; }
        .chart-container { position: relative; width: 100%; height: 320px; margin-bottom: 20px; }

        .side-panel { background: var(--card-bg); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 20px; display: flex; flex-direction: column; gap: 20px; }
        
        .leaderboard-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
        .input-box { width: 90%; background: #05060b; border: 1px solid rgba(255,255,255,0.15); color: #fff; padding: 8px; border-radius: 6px; margin-top: 4px; font-weight: bold; }

        .up { color: var(--neon-green); text-shadow: 0 0 8px rgba(0,255,102,0.2); }
        .down { color: var(--neon-magenta); text-shadow: 0 0 8px rgba(255,0,85,0.2); }

        .actions-container { display: flex; gap: 15px; justify-content: center; align-items: center; flex-wrap: wrap; }
        .btn {
            background: rgba(255, 255, 255, 0.02); border: 2px solid transparent; color: white;
            padding: 12px 35px; font-size: 1rem; font-weight: bold; border-radius: 8px;
            cursor: pointer; text-transform: uppercase; transition: all 0.2s;
        }
        .btn-buy { border-color: var(--neon-green); }
        .btn-buy:hover { background: var(--neon-green); color: #000; box-shadow: 0 0 15px rgba(0, 255, 102, 0.4); }
        .btn-sell { border-color: var(--neon-magenta); }
        .btn-sell:hover { background: var(--neon-magenta); color: #fff; box-shadow: 0 0 15px rgba(255, 0, 85, 0.4); }
        
        #btn-loan { border-color: #eab308; color: #eab308; display: none; }
        #btn-loan:hover { background: #eab308; color: #000; box-shadow: 0 0 15px rgba(234, 179, 8, 0.4); }

        #notification-box {
            position: fixed; bottom: 20px; right: 20px; background: #0a0b16;
            border: 1px solid var(--neon-cyan); padding: 15px 25px; border-radius: 8px;
            color: #fff; display: none; z-index: 1000; font-weight: bold;
        }
    </style>
</head>
<body>

    <div class="news-ticker">
        <div id="news-banner" class="news-content">{{ current_news }}</div>
    </div>

    <h1>Neon Trading Empire</h1>

    <div class="game-container">
        <div class="portfolio-panel">
            <div class="stat-box">
                <div class="stat-label">VALEUR NETTE (SCORE)</div>
                <div id="p-networth" class="stat-value">1000.00 $</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">SOLDE LIQUIDE</div>
                <div id="p-cash" class="stat-value">{{ player.cash }} $</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">RENDEMENT RENDU</div>
                <div class="stat-value" style="color: #64748b;">2.0% / 2 min</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">TAXE COURTAGE</div>
                <div class="stat-value" style="color: var(--neon-magenta);">1.00 $ / Ordre</div>
            </div>
        </div>

        <div class="market-grid">
            {% for ticker, stock in stocks.items() %}
            <div id="card-{{ ticker }}" class="stock-card {% if ticker == 'NNT' %}active{% endif %}" onclick="selectStock('{{ ticker }}')">
                <div class="stock-card-header">
                    <div>
                        <strong style="font-size: 1.1rem; color: #fff;">{{ stock.name }}</strong>
                        <div style="font-size: 0.85rem; color: #64748b; margin-top:4px;">Possédé: <span id="owned-{{ ticker }}" style="color: var(--neon-cyan);">{{ player.shares[ticker] }}</span></div>
                    </div>
                    <div style="text-align: right;">
                        <div id="price-{{ ticker }}" style="font-size: 1.3rem; font-weight: bold;">{{ stock.price }} $</div>
                        <div id="change-{{ ticker }}" style="font-size: 0.85rem;" class="up">0.00%</div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="main-layout-grid">
            <div class="main-panel">
                <h2 id="active-title" style="margin-top:0; color: var(--neon-cyan);">NEON_TECH (NNT)</h2>
                <div class="chart-container">
                    <canvas id="mainChart"></canvas>
                </div>
                <div class="actions-container">
                    <button class="btn btn-buy" onclick="buyActiveStock()">Acheter 1 Part</button>
                    <button class="btn btn-sell" onclick="sellActiveStock()">Vendre 1 Part</button>
                    <button id="btn-loan" class="btn" onclick="triggerLoan()">⚠️ Prêt d'urgence</button>
                </div>
            </div>

            <div class="side-panel">
                <div>
                    <h3 style="color: var(--neon-magenta); text-shadow: 0 0 5px var(--neon-magenta);">🏆 CLASSEMENT IA</h3>
                    <div id="leaderboard-container">
                        <div class="leaderboard-row"><span>🥇 Vous (Trader)</span><span style="font-weight:bold; color:var(--neon-green)">1000.00 $</span></div>
                        <div class="leaderboard-row"><span>🥈 🕶️ Gordon Gekko AI</span><span>1000.00 $</span></div>
                        <div class="leaderboard-row"><span>🥉 🐋 Crypto Whale 99</span><span>1000.00 $</span></div>
                    </div>
                </div>

                <div>
                    <h3 style="color: var(--neon-cyan); text-shadow: 0 0 5px var(--neon-cyan);">⚙️ ORDRES AUTO (<span id="orders-ticker">NNT</span>)</h3>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div>
                            <span class="stat-label">Stop-Loss ($) [Plancher] :</span>
                            <input type="number" id="input-sl" placeholder="Ex: 85" step="0.1" class="input-box">
                        </div>
                        <div>
                            <span class="stat-label">Take-Profit ($) [Plafond] :</span>
                            <input type="number" id="input-tp" placeholder="Ex: 140" step="0.1" class="input-box">
                        </div>
                        <div style="display:flex; gap: 10px; margin-top: 5px;">
                            <button class="btn" style="padding: 6px 14px; font-size: 0.8rem; border-color: var(--neon-cyan);" onclick="saveAutoOrders()">Activer</button>
                            <button class="btn" style="padding: 6px 14px; font-size: 0.8rem; border-color: #64748b;" onclick="clearAutoOrders()">Effacer</button>
                        </div>
                        <div style="font-size: 0.8rem; color: #64748b; margin-top: 5px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                            Statut : SL: <span id="status-sl" style="color: var(--neon-magenta); font-weight:bold;">Aucun</span> | TP: <span id="status-tp" style="color: var(--neon-green); font-weight:bold;">Aucun</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="notification-box"></div>

    <script>
        let stocksData = {{ stocks|tojson }};
        let playerOrders = {{ player.limit_orders|tojson }};
        let currentTicker = "NNT";

        const ctx = document.getElementById('mainChart').getContext('2d');
        const neonGradient = ctx.createLinearGradient(0, 0, 0, 300);
        neonGradient.addColorStop(0, 'rgba(0, 243, 255, 0.15)');
        neonGradient.addColorStop(1, 'rgba(0, 243, 255, 0.0)');

        const mainChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: stocksData[currentTicker].labels,
                datasets: [{
                    data: stocksData[currentTicker].history,
                    borderColor: '#00f3ff', borderWidth: 3, backgroundColor: neonGradient, fill: true, tension: 0.2, pointRadius: 2
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.01)' }, ticks: { color: '#64748b' } },
                    y: { grid: { color: 'rgba(255,255,255,0.01)' }, ticks: { color: '#64748b' } }
                }
            }
        });

        function selectStock(ticker) {
            currentTicker = ticker;
            document.querySelectorAll('.stock-card').forEach(c => c.classList.remove('active'));
            document.getElementById(`card-${ticker}`).classList.add('active');
            document.getElementById('active-title').innerText = stocksData[ticker].name;
            
            mainChart.data.labels = stocksData[ticker].labels;
            mainChart.data.datasets[0].data = stocksData[ticker].history;
            mainChart.update();
            
            updateOrdersUI();
        }

        function updateOrdersUI() {
            document.getElementById('orders-ticker').innerText = currentTicker;
            const o = playerOrders[currentTicker] || {stop_loss: null, take_profit: null};
            document.getElementById('status-sl').innerText = o.stop_loss ? o.stop_loss.toFixed(2) + " $" : "Aucun";
            document.getElementById('status-tp').innerText = o.take_profit ? o.take_profit.toFixed(2) + " $" : "Aucun";
        }

        const socket = io();
        function buyActiveStock() { socket.emit('buy_stock', { ticker: currentTicker }); }
        function sellActiveStock() { socket.emit('sell_stock', { ticker: currentTicker }); }
        function triggerLoan() { socket.emit('emergency_loan'); }
        
        function saveAutoOrders() {
            const sl = document.getElementById('input-sl').value;
            const tp = document.getElementById('input-tp').value;
            socket.emit('set_limits', { ticker: currentTicker, sl: sl, tp: tp });
        }
        function clearAutoOrders() {
            document.getElementById('input-sl').value = "";
            document.getElementById('input-tp').value = "";
            socket.emit('set_limits', { ticker: currentTicker, sl: null, tp: null });
        }

        socket.on('news_flash', function(data) {
            const banner = document.getElementById('news-banner');
            banner.style.animation = 'none'; banner.offsetHeight;
            banner.innerText = data.message;
            banner.style.animation = 'marquee 25s linear infinite';
        });

        socket.on('market_update', function(data) {
            stocksData[data.ticker].price = data.price;
            stocksData[data.ticker].history = data.history;
            stocksData[data.ticker].labels = data.labels;

            const cardPrice = document.getElementById(`price-${data.ticker}`);
            const cardChange = document.getElementById(`change-${data.ticker}`);
            cardPrice.innerText = data.price.toFixed(2) + " $";
            cardChange.innerText = (data.change >= 0 ? "+" : "") + data.change.toFixed(2) + "%";
            cardChange.className = data.change >= 0 ? "up" : "down";

            if (data.net_worth) {
                document.getElementById('p-networth').innerText = data.net_worth.toFixed(2) + " $";
            }

            if (data.leaderboard) {
                let lbHtml = "";
                data.leaderboard.forEach((user, idx) => {
                    let medal = idx === 0 ? "🥇 " : idx === 1 ? "🥈 " : "🥉 ";
                    let isPlayer = user.name.includes("Vous");
                    lbHtml += `<div class="leaderboard-row">
                        <span>${medal}${user.name}</span>
                        <span style="font-weight:bold; color:${isPlayer ? 'var(--neon-green)' : '#fff'}">${user.net_worth.toFixed(2)} $</span>
                    </div>`;
                });
                document.getElementById('leaderboard-container').innerHTML = lbHtml;
            }

            if (data.ticker === currentTicker) {
                mainChart.data.labels = data.labels;
                mainChart.data.datasets[0].data = data.history;
                mainChart.data.datasets[0].borderColor = data.change >= 0 ? '#00ff66' : '#ff0055';
                mainChart.update('none');
            }
        });

        socket.on('player_update', function(player) {
            document.getElementById('p-cash').innerText = player.cash.toFixed(2) + " $";
            if (player.net_worth) {
                document.getElementById('p-networth').innerText = player.net_worth.toFixed(2) + " $";
            }
            
            let totalShares = 0;
            for (let ticker in player.shares) {
                document.getElementById(`owned-${ticker}`).innerText = player.shares[ticker];
                totalShares += player.shares[ticker];
            }

            if (player.limit_orders) {
                playerOrders = player.limit_orders;
                updateOrdersUI();
            }

            const loanBtn = document.getElementById('btn-loan');
            if (player.cash < 5.0 && totalShares === 0) {
                loanBtn.style.display = "inline-block";
            } else {
                loanBtn.style.display = "none";
            }
        });

        socket.on('notification', function(data) {
            const box = document.getElementById('notification-box');
            box.innerText = data.message; box.style.display = 'block';
            setTimeout(() => { box.style.display = 'none'; }, 4000);
        });
        
        updateOrdersUI();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """ FIX : Rendu initial de l'interface web """
    return render_template_string(
        HTML_TEMPLATE, 
        stocks=game_state["stocks"], 
        player=game_state["player"], 
        current_news=game_state["current_news"]
    )

if __name__ == '__main__':
    thread = Thread(target=market_simulation)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
