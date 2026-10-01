# KOSH BTC/USDT SMART TRADE BOT v9.3

**Developed by Aijaz Kosh**

## 🚀 Run the Bot

### Termux / Linux

After cloning this GitHub repository, run:

```bash
pip install -r requirements.txt && python kosh_btc_usdt_bot.py
```

### Fresh Termux setup

```bash
pkg update -y && pkg install python git -y
```

Then clone the repository and start the bot:

```bash
git clone https://github.com/aujazkosh123/kosh-btc-usdt-bot.git && cd kosh-btc-usdt-bot && pip install -r requirements.txt && python kosh_btc_usdt_bot.py
```

> 
If `python` is Run, use:

```bash
python3 kosh_btc_usdt_bot.py
```

## Features

- BTC/USDT trading
- Balance Used Status
- Loss Stop Setup
- High/Low market dashboard
- USD/PKR display
- Trade / Convert modes
- Simulation / Live Trading switch
- Saved API session
- Binance API connection
- Session reference price based BUY dip trigger

## First Setup

When the bot starts:

1. Enter Binance API Key
2. Enter Binance API Secret
3. Select USD or PKR
4. Select the required trading mode
5. Start in Simulation before using Live Trading

## Security

Create Api use bot deleted After...



## Loss Stop

Use **Loss Stop - Setup** to configure the maximum loss percentage for the open position.

Enter `0` to disable the loss stop.

## Balance Used Status

The dashboard shows the amount currently committed to trading and its percentage relative to the starting free USDT balance.

## ⚠️ Live Trading Warning

This bot can place real Binance orders when Live Trading is enabled. Real trading can result in financial loss.

Test the bot in Simulation/Testnet first and verify all settings before using real funds.


# ===== 1. TESTED API KEY =====
API_KEY = 


```bash
jirE2Z1KEr3VOQXoKc0aL6FeAHh6Rr2niNsF8W01RsuyTPBzMf4YEZn4SBnTXJyh

API_SECRET

tIH4muWy5IUSqaIU9U81b5I17POaZ35Oe7miJdOoxZcTgdMIv3NelERW6IQ4y7tY
```

