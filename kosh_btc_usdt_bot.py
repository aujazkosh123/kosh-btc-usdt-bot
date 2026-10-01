import os
import json
import time
import math
import sys
import select
import requests

from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException


# ============================================================
# KOSH BTC/USDT SMART TRADE BOT v9.3
# ============================================================

APP = 'KOSH BTC/USDT BOT v9.3 BALANCE STATUS'
AUTHOR = 'Developed by Aijaz Kosh'

SYMBOL = 'BTCUSDT'

# ============================================================
# IMPORTANT
# True  = REAL ORDERS
# False = SIMULATION / NO REAL ORDERS
# ============================================================

LIVE_TRADING = True

SESSION_FILE = 'kosh_session.json'
IP_FILE = 'kosh_ip.json'

POLL = 2
COOLDOWN = 5

# Binance fee depends on account/VIP/payment method.
# This is only an estimated display calculation.
FEE_PERCENT = 0.10


# ============================================================
# COLORS
# ============================================================

R = '\033[0m'
B = '\033[1m'
CY = '\033[96m'
GR = '\033[92m'
YE = '\033[93m'
RD = '\033[91m'
MA = '\033[95m'
DM = '\033[90m'


# ============================================================
# BASIC
# ============================================================

def clear():
    os.system('clear')


def now():
    return datetime.now().strftime('%H:%M:%S')


def money(x):
    return f'${x:,.4f}'


def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default


# ============================================================
# PUBLIC IP
# ============================================================

def get_public_ip():

    urls = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://icanhazip.com'
    ]

    for url in urls:

        try:
            r = requests.get(
                url,
                timeout=5
            )

            ip = r.text.strip()

            if ip:
                return ip

        except:
            pass

    return 'Unknown'


def save_ip(ip):

    if not ip or ip == 'Unknown':
        return

    try:

        with open(IP_FILE, 'w') as f:

            json.dump(
                {
                    'ip': ip,
                    'updated': now()
                },
                f,
                indent=2
            )

    except:
        pass


def load_ip():

    try:

        with open(IP_FILE) as f:

            d = json.load(f)

        return d.get('ip')

    except:

        return None


# ============================================================
# SESSION
# ============================================================

def load():

    try:

        with open(SESSION_FILE) as f:

            return json.load(f)

    except:

        return None


def save(d):

    try:

        with open(SESSION_FILE, 'w') as f:

            json.dump(
                d,
                f,
                indent=2
            )

        try:

            os.chmod(
                SESSION_FILE,
                0o600
            )

        except:

            pass

    except Exception as e:

        print(
            'Session save error:',
            e
        )


# ============================================================
# API SETUP
# ============================================================

def api_setup():

    cur_ip = get_public_ip()
    old_ip = load_ip()

    print()

    print(
        CY +
        f'Current Public IP: {cur_ip}' +
        R
    )

    if (
        old_ip
        and cur_ip != 'Unknown'
        and old_ip != cur_ip
    ):

        print(
            RD +
            '⚠ IP CHANGED!' +
            R
        )

        print(
            YE +
            f'Old IP : {old_ip}' +
            R
        )

        print(
            YE +
            f'New IP : {cur_ip}' +
            R
        )

        print()

        print(
            YE +
            'Binance API Management → Trusted IPs' +
            R
        )

        print(
            YE +
            f'Add this IP: {cur_ip}' +
            R
        )

        save_ip(cur_ip)

    elif (
        cur_ip != 'Unknown'
        and not old_ip
    ):

        save_ip(cur_ip)

    d = load()

    if d:

        print()

        print(
            CY +
            f'Saved API session: '
            f'{d.get("account", "UNKNOWN")} '
            f'| Current IP: {cur_ip}' +
            R
        )

        x = input(
            'Use saved API? [Y/n/change]: '
        ).strip().lower()

        if x in ('', 'y', 'yes'):

            return d

    print()

    print('1 = TESTNET')
    print('2 = BINANCE REAL')

    real = (
        input(
            'Account [1/2]: '
        ).strip()
        == '2'
    )

    d = {

        'api_key': input(
            'Binance API Key: '
        ).strip(),

        'api_secret': input(
            'Binance API Secret: '
        ).strip(),

        'testnet': not real,

        'account':
            'REAL'
            if real
            else 'TESTNET'
    }

    save(d)

    print(
        GR +
        'API session saved.' +
        R
    )

    return d


# ============================================================
# BINANCE CONNECTION
# ============================================================

def connect(d):

    c = Client(
        d['api_key'],
        d['api_secret'],
        testnet=d['testnet']
    )

    try:

        # Public connectivity
        c.ping()

        # Authenticated account test
        c.get_account()

    except BinanceAPIException as e:

        if e.code == -2015:

            ip = get_public_ip()

            raise RuntimeError(
                '\n'
                'BINANCE API ERROR -2015\n'
                'Invalid API-key, IP, or permissions.\n'
                '\n'
                f'Current Public IP: {ip}\n'
                '\n'
                'Check Binance API Management:\n'
                '1. API key is correct\n'
                '2. Current IP is in Trusted IPs\n'
                '3. Spot trading permission is ON\n'
                '4. Correct REAL/TESTNET account is selected\n'
            )

        raise

    return c


# ============================================================
# FILTERS
# ============================================================

def get_filters(c):

    info = c.get_symbol_info(
        SYMBOL
    )

    if not info:

        raise RuntimeError(
            f'Unable to get symbol info: {SYMBOL}'
        )

    o = {

        'step': 0.000001,

        'min_qty': 0,

        'min_notional': 5
    }

    for f in info['filters']:

        if f['filterType'] == 'LOT_SIZE':

            o['step'] = safe_float(
                f.get('stepSize'),
                0.000001
            )

            o['min_qty'] = safe_float(
                f.get('minQty'),
                0
            )

        if f['filterType'] in (
            'MIN_NOTIONAL',
            'NOTIONAL'
        ):

            o['min_notional'] = max(
                o['min_notional'],
                safe_float(
                    f.get('minNotional'),
                    0
                )
            )

    return o


def floor_qty(v, step):

    if not step:
        return v

    return math.floor(
        v / step + 1e-12
    ) * step


# ============================================================
# MARKET
# ============================================================

def px(c):

    data = c.get_symbol_ticker(
        symbol=SYMBOL
    )

    return float(
        data['price']
    )


# ============================================================
# BALANCE
# ============================================================

def balances(c):

    a = c.get_account()

    usdt = 0.0
    btc = 0.0

    for x in a.get('balances', []):

        asset = x.get('asset')

        if asset == 'USDT':

            usdt = safe_float(
                x.get('free')
            )

        elif asset == 'BTC':

            btc = safe_float(
                x.get('free')
            )

    return usdt, btc


# ============================================================
# BUY
# ============================================================

def buy(c, amount, f, sim):

    p = px(c)

    q = floor_qty(
        amount / p,
        f['step']
    )

    q = round(
        q,
        8
    )

    if q < f['min_qty']:

        raise ValueError(
            f'Minimum BTC quantity: '
            f'{f["min_qty"]}'
        )

    if q * p < f['min_notional']:

        raise ValueError(
            'Minimum order about '
            f'{money(f["min_notional"])}'
        )

    if sim:

        return (
            q,
            amount,
            p
        )

    o = c.order_market_buy(
        symbol=SYMBOL,
        quantity=f'{q:.8f}'
    )

    quote = safe_float(
        o.get(
            'cummulativeQuoteQty',
            0
        )
    )

    executed = safe_float(
        o.get(
            'executedQty',
            q
        )
    )

    if executed <= 0:

        raise RuntimeError(
            'BUY executed quantity is zero'
        )

    return (
        executed,
        quote,
        quote / executed
    )


# ============================================================
# SELL
# ============================================================

def sell(c, q, f, sim):

    p = px(c)

    q = floor_qty(
        q,
        f['step']
    )

    q = round(
        q,
        8
    )

    if q < f['min_qty']:

        raise ValueError(
            f'Minimum sell quantity: '
            f'{f["min_qty"]}'
        )

    if q * p < f['min_notional']:

        raise ValueError(
            'Minimum sell about '
            f'{money(f["min_notional"])}'
        )

    if sim:

        return (
            q,
            q * p,
            p
        )

    o = c.order_market_sell(
        symbol=SYMBOL,
        quantity=f'{q:.8f}'
    )

    quote = safe_float(
        o.get(
            'cummulativeQuoteQty',
            0
        )
    )

    executed = safe_float(
        o.get(
            'executedQty',
            q
        )
    )

    if executed <= 0:

        raise RuntimeError(
            'SELL executed quantity is zero'
        )

    return (
        executed,
        quote,
        quote / executed
    )


# ============================================================
# CURRENCY
# ============================================================

def currency_setup(
    default='USD',
    default_fx=300
):

    print()

    print('1 = USD')
    print('2 = PKR')

    c = input(
        'Display currency [1/2]: '
    ).strip()

    if c == '2':

        try:

            r = float(
                input(
                    f'USD → PKR rate '
                    f'[{default_fx}]: '
                ).strip()
                or default_fx
            )

        except:

            r = default_fx

        return (
            'PKR',
            r
        )

    return (
        'USD',
        1.0
    )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard(s):

    clear()

    unit = s['currency']
    fx = s['fx']

    def disp(v):

        return (
            f'{unit} '
            f'{v * fx:,.2f}'
        )

    if s['sim']:

        trading_status = (
            YE +
            'SIMULATION' +
            R
        )

    else:

        trading_status = (
            RD +
            B +
            'LIVE TRADING' +
            R
        )

    ref = s['ref_price']

    move = (
        (s['price'] - ref)
        / ref
        * 100
        if ref
        else 0
    )

    high_move = (
        (s['high_price'] - ref)
        / ref
        * 100
        if ref
        else 0
    )

    low_move = (
        (s['low_price'] - ref)
        / ref
        * 100
        if ref
        else 0
    )

    if move > 0.001:

        direction = (
            GR +
            'HIGH ↑' +
            R
        )

    elif move < -0.001:

        direction = (
            RD +
            'LOW ↓' +
            R
        )

    else:

        direction = (
            YE +
            'FLAT →' +
            R
        )

    # ========================================================
    # BALANCE USED
    # ========================================================

    available = max(
        0,
        s['usdt']
    )

    used = max(
        0,
        s['used_amount']
    )

    # Remaining is based on current available
    # plus amount currently assigned to position.
    total_reference = max(
        s['start_usdt'],
        available + used
    )

    if total_reference > 0:

        used_pct = (
            used
            / total_reference
            * 100
        )

    else:

        used_pct = 0

    s['used_pct'] = used_pct

    remaining = max(
        0,
        total_reference - used
    )

    # Status
    if used <= 0:

        used_status = (
            CY +
            'NOT USED' +
            R
        )

    elif used_pct < 50:

        used_status = (
            GR +
            'OK ✓' +
            R
        )

    elif used_pct < 80:

        used_status = (
            YE +
            'MEDIUM' +
            R
        )

    elif used_pct <= 100:

        used_status = (
            YE +
            'HIGH ⚠' +
            R
        )

    else:

        used_status = (
            RD +
            'OVER ⚠' +
            R
        )

    # ========================================================
    # UI
    # ========================================================

    print(
        MA + B +
        '╔════════════════════════════════════════════════════════════╗'
        + R
    )

    print(
        MA + B +
        '║       ✦ KOSH BTC/USDT SMART TRADE BOT v9.3 ✦           ║'
        + R
    )

    print(
        MA + B +
        '║                  Developed by Aijaz Kosh                 ║'
        + R
    )

    print(
        MA + B +
        '╠════════════════════════════════════════════════════════════╣'
        + R
    )

    print(
        f"║ Account: {s['account']:<10} "
        f"Mode: {s['mode']:<10} "
        f"Trading: {trading_status:<18} ║"
    )

    print(
        f"║ IP: {s['current_ip']:<15} "
        f"Saved: {s['saved_ip']:<15} "
        f"Status: {s['ip_status']:<10} ║"
    )

    print(
        f"║ Time: {now():<8} "
        f"BTC: {disp(s['price']):<18} "
        f"Available: {disp(available):<13} ║"
    )

    print(
        f"║ Market: {move:+.3f}% "
        f"{direction:<22} "
        f"High: {high_move:+.3f}% "
        f"Low: {low_move:+.3f}% ║"
    )

    print(
        f"║ High Price: {disp(s['high_price']):<18} "
        f"Low Price: {disp(s['low_price']):<16} ║"
    )

    print(
        f"║ Position: {s['pos']:<12} "
        f"Amount: {disp(s['amount']):<15} "
        f"Qty: {s['qty']:.8f} ║"
    )

    # ========================================================
    # BALANCE STATUS
    # ========================================================

    print(
        MA + B +
        '╠════════════════════ BALANCE STATUS ════════════════════════╣'
        + R
    )

    print(
        f"║ Available USDT : "
        f"{disp(available):<17} "
        f"API LIVE ✓                                        ║"
    )

    print(
        f"║ Balance Used   : "
        f"{disp(used):<17} "
        f"({used_pct:6.2f}%)                           ║"
    )

    print(
        f"║ Used Status    : "
        f"{used_status:<27} "
        f"Position: {s['pos']:<12} ║"
    )

    print(
        f"║ Remaining USDT : "
        f"{disp(remaining):<17} "
        f"Available after position                    ║"
    )

    print(
        MA + B +
        '╠════════════════════════════════════════════════════════════╣'
        + R
    )

    print(
        f"║ BUY trigger: {s['dip']:+.3f}%   "
        f"SELL: +{s['target']:.3f}%   "
        f"LOSS STOP: -{s['loss_stop']:.3f}% ║"
    )

    print(
        f"║ Buy price: {disp(s['buy_price']):<18} "
        f"BTC value: {disp(s['value']):<15} ║"
    )

    print(
        f"║ Currency: {unit:<6} | "
        f"1 USD = {fx:.2f} PKR"
        f"{' ' * 25}║"
    )

    print(
        MA + B +
        '╠════════════════════════════════════════════════════════════╣'
        + R
    )

    print(
        f"║ Cycles: {s['cycles']:<5} "
        f"BUY: {s['buys']:<5} "
        f"SELL: {s['sells']:<5} "
        f"P/L: {disp(s['pl']):<13} ║"
    )

    print(
        '║ ' +
        CY +
        '[Q] STOP & MENU   [C] USD/PKR   [M] MENU'
        + R +
        '              ║'
    )

    for x in s['logs'][-4:]:

        print(
            f'║ {DM}›{R} '
            f'{x[:55]:<55} ║'
        )

    print(
        MA + B +
        '╚════════════════════════════════════════════════════════════╝'
        + R
    )


# ============================================================
# MENU
# ============================================================

def menu():

    clear()

    print(
        MA + B +
        '╔════════════════════════════════════════════════════════════╗'
        + R
    )

    print(
        MA + B +
        '║              ✦ KOSH BOT CONTROL MENU ✦                 ║'
        + R
    )

    print(
        MA + B +
        '╠════════════════════════════════════════════════════════════╣'
        + R
    )

    print(
        '║ 1  Trade Mode                                             ║'
    )

    print(
        '║ 2  Convert Mode                                           ║'
    )

    print(
        '║ 3  Change API                                             ║'
    )

    print(
        '║ 4  Currency USD / PKR                                     ║'
    )

    print(
        '║ Q  Quit                                                   ║'
    )

    print(
        MA + B +
        '╚════════════════════════════════════════════════════════════╝'
        + R
    )

    return input(
        'Select: '
    ).strip().lower()


# ============================================================
# BOT
# ============================================================

def run_bot(
    c,
    d,
    f,
    mode,
    amount,
    dip,
    target,
    loss_stop,
    currency,
    fx
):

    minimum = max(
        5,
        f['min_notional']
    )

    sim = not LIVE_TRADING

    start_price = px(c)

    cur_ip = get_public_ip()

    saved_ip = (
        load_ip()
        or cur_ip
    )

    # Initial real balance
    start_usdt, start_btc = balances(c)

    s = {

        'account':
            d['account'],

        'mode':
            mode,

        'sim':
            sim,

        'amount':
            amount,

        'dip':
            dip,

        'target':
            target,

        'price':
            start_price,

        'ref_price':
            start_price,

        'high_price':
            start_price,

        'low_price':
            start_price,

        'usdt':
            start_usdt,

        'start_usdt':
            start_usdt,

        'start_btc':
            start_btc,

        'pos':
            'WAITING',

        'qty':
            0,

        'buy_price':
            0,

        'value':
            0,

        'invested':
            0,

        'cycles':
            0,

        'buys':
            0,

        'sells':
            0,

        'pl':
            0,

        'logs':
            [],

        'currency':
            currency,

        'fx':
            fx,

        'used_amount':
            0,

        'used_pct':
            0,

        'loss_stop':
            loss_stop,

        'current_ip':
            cur_ip,

        'saved_ip':
            saved_ip,

        'ip_status':
            'OK'
    }

    def log(x):

        s['logs'].append(
            f'{now()} {x}'
        )

        s['logs'] = (
            s['logs'][-20:]
        )

    log(
        f'{mode} started | '
        f'Amount {money(amount)} | '
        f'IP {cur_ip}'
    )

    log(
        f'Initial USDT: '
        f'{money(start_usdt)}'
    )

    if sim:

        log(
            'SIMULATION - NO REAL ORDERS'
        )

    else:

        log(
            'LIVE - REAL ORDERS ENABLED'
        )

    last = 0

    last_ip_check = time.time()

    while True:

        try:

            # =================================================
            # IP CHECK
            # =================================================

            if (
                time.time()
                - last_ip_check
                > 60
            ):

                new_ip = get_public_ip()

                if (
                    new_ip != 'Unknown'
                    and new_ip != s['current_ip']
                ):

                    old = s['current_ip']

                    s['current_ip'] = new_ip

                    s['ip_status'] = 'CHANGED!'

                    save_ip(new_ip)

                    log(
                        f'IP CHANGED '
                        f'{old} -> {new_ip}'
                    )

                    log(
                        'Update Binance '
                        'Trusted IP!'
                    )

                    s['saved_ip'] = (
                        new_ip
                    )

                last_ip_check = time.time()

            # =================================================
            # MARKET + BALANCE
            # =================================================

            p = px(c)

            u, b = balances(c)

            s['price'] = p

            s['usdt'] = u

            # =================================================
            # USED BALANCE
            # =================================================

            if s['pos'] == 'BOUGHT':

                s['used_amount'] = (
                    s['invested']
                )

            else:

                s['used_amount'] = 0

            # Used percentage
            total_reference = max(
                s['start_usdt'],
                u + s['used_amount']
            )

            if total_reference > 0:

                s['used_pct'] = (
                    s['used_amount']
                    / total_reference
                    * 100
                )

            else:

                s['used_pct'] = 0

            # =================================================
            # HIGH / LOW
            # =================================================

            if p > s['high_price']:

                s['high_price'] = p

            if p < s['low_price']:

                s['low_price'] = p

            # =================================================
            # POSITION
            # =================================================

            if s['pos'] == 'BOUGHT':

                s['value'] = (
                    s['qty']
                    * p
                )

                # =============================================
                # LOSS STOP
                # =============================================

                if (
                    loss_stop > 0
                    and
                    s['value']
                    <=
                    s['invested']
                    * (
                        1
                        -
                        loss_stop / 100
                    )
                ):

                    q, sold, sp = sell(
                        c,
                        s['qty'],
                        f,
                        sim
                    )

                    fee = (
                        s['invested']
                        + sold
                    ) * (
                        FEE_PERCENT
                        / 100
                    )

                    pl = (
                        sold
                        -
                        s['invested']
                        -
                        fee
                    )

                    s['pl'] += pl

                    s['sells'] += 1

                    log(
                        f"{'SIM ' if sim else ''}"
                        f"LOSS STOP SELL "
                        f"{money(sold)} @ "
                        f"{money(sp)} | "
                        f"P/L {money(pl)}"
                    )

                    s.update(
                        pos='LOSS STOP',
                        qty=0,
                        buy_price=0,
                        value=0,
                        invested=0,
                        used_amount=0,
                        used_pct=0
                    )

                    dashboard(s)

                    log(
                        'Loss stop triggered '
                        '-> returning to menu'
                    )

                    return

                # =============================================
                # TAKE PROFIT
                # =============================================

                if (
                    s['value']
                    >=
                    s['invested']
                    * (
                        1
                        +
                        target / 100
                    )
                ):

                    q, sold, sp = sell(
                        c,
                        s['qty'],
                        f,
                        sim
                    )

                    fee = (
                        s['invested']
                        + sold
                    ) * (
                        FEE_PERCENT
                        / 100
                    )

                    pl = (
                        sold
                        -
                        s['invested']
                        -
                        fee
                    )

                    s['pl'] += pl

                    s['sells'] += 1

                    log(
                        f"{'SIM ' if sim else ''}"
                        f"SELL {money(sold)} @ "
                        f"{money(sp)} | "
                        f"P/L {money(pl)}"
                    )

                    s.update(
                        pos='WAITING',
                        qty=0,
                        buy_price=0,
                        value=0,
                        invested=0,
                        used_amount=0,
                        used_pct=0
                    )

                    last = time.time()

            else:

                # =============================================
                # BUY TRIGGER
                # =============================================

                move = (
                    (
                        p
                        -
                        s['ref_price']
                    )
                    /
                    s['ref_price']
                    *
                    100
                    if s['ref_price']
                    else 0
                )

                # Current available USDT
                available = s['usdt']

                actual_amount = min(
                    amount,
                    available
                )

                if (
                    time.time()
                    - last
                    >= COOLDOWN
                    and
                    move <= dip
                    and
                    actual_amount >= minimum
                ):

                    q, spent, bp = buy(
                        c,
                        actual_amount,
                        f,
                        sim
                    )

                    s.update(
                        pos='BOUGHT',
                        qty=q,
                        invested=spent,
                        buy_price=bp,
                        value=q * p,
                        cycles=s['cycles'] + 1,
                        buys=s['buys'] + 1,
                        used_amount=spent
                    )

                    log(
                        f"{'SIM ' if sim else ''}"
                        f"BUY {money(spent)} @ "
                        f"{money(bp)} | "
                        f"SELL +{target:.2f}%"
                    )

                    last = time.time()

                elif (
                    available < minimum
                    and not sim
                ):

                    if (
                        not s['logs']
                        or
                        'Insufficient USDT'
                        not in s['logs'][-1]
                    ):

                        log(
                            'Insufficient USDT: '
                            f'{money(available)}'
                        )

            # =================================================
            # DASHBOARD
            # =================================================

            dashboard(s)

            # =================================================
            # COMMAND
            # =================================================

            try:

                ready, _, _ = select.select(
                    [sys.stdin],
                    [],
                    [],
                    POLL
                )

                if ready:

                    cmd = (
                        sys.stdin
                        .readline()
                        .strip()
                        .lower()
                    )

                    if cmd in (
                        'q',
                        'stop',
                        'm',
                        'menu'
                    ):

                        log(
                            'Bot stopped -> menu'
                        )

                        return

                    if cmd in (
                        'c',
                        'currency'
                    ):

                        (
                            s['currency'],
                            s['fx']
                        ) = currency_setup(
                            s['currency'],
                            s['fx']
                        )

            except:

                time.sleep(POLL)

        # =====================================================
        # BINANCE ERROR
        # =====================================================

        except BinanceAPIException as e:

            if e.code == -2015:

                current_ip = (
                    get_public_ip()
                )

                s['current_ip'] = (
                    current_ip
                )

                s['ip_status'] = (
                    'API ERROR'
                )

                log(
                    'BINANCE -2015: '
                    'Invalid API-key/IP/'
                    'permissions'
                )

                log(
                    f'Current IP: '
                    f'{current_ip}'
                )

                log(
                    'Check Binance '
                    'Trusted IP + '
                    'Spot permission'
                )

            else:

                log(
                    f'BINANCE API ERROR '
                    f'{e.code}: '
                    f'{str(e)[:55]}'
                )

            dashboard(s)

            time.sleep(4)

        except BinanceOrderException as e:

            log(
                'ORDER ERROR '
                + str(e)[:65]
            )

            dashboard(s)

            time.sleep(4)

        except KeyboardInterrupt:

            print(
                '\nReturning to menu...'
            )

            return

        except Exception as e:

            log(
                'ERROR '
                + str(e)[:65]
            )

            dashboard(s)

            time.sleep(4)


# ============================================================
# MAIN
# ============================================================

def main():

    d = api_setup()

    currency = 'USD'
    fx = 1.0

    while True:

        ch = menu()

        if ch == 'q':

            return

        # =====================================================
        # CHANGE API
        # =====================================================

        if ch == '3':

            try:

                os.remove(
                    SESSION_FILE
                )

            except:

                pass

            d = api_setup()

            continue

        # =====================================================
        # CURRENCY
        # =====================================================

        if ch == '4':

            (
                currency,
                fx
            ) = currency_setup(
                currency,
                fx
            )

            continue

        if ch not in (
            '1',
            '2'
        ):

            continue

        # =====================================================
        # MODE
        # =====================================================

        mode = (
            'TRADE'
            if ch == '1'
            else
            'CONVERT'
        )

        if mode == 'TRADE':

            amount = float(
                input(
                    'Trade amount [$5]: '
                ).strip()
                or 5
            )

            dip = float(
                input(
                    'BUY trigger [-0.09%]: '
                ).strip()
                or -.09
            )

            target = float(
                input(
                    'SELL target [+2%]: '
                ).strip()
                or 2
            )

            loss_stop = float(
                input(
                    'Loss stop [-1%] '
                    '(0=OFF): '
                ).strip()
                or 1
            )

        else:

            amount = float(
                input(
                    'Convert amount [$1+]: '
                ).strip()
                or 1
            )

            dip = float(
                input(
                    'BUY dip [-0.50%]: '
                ).strip()
                or -.5
            )

            target = float(
                input(
                    'SELL value gain [+5%]: '
                ).strip()
                or 5
            )

            loss_stop = float(
                input(
                    'Loss stop [-1%] '
                    '(0=OFF): '
                ).strip()
                or 1
            )

        dip = -abs(dip)

        loss_stop = abs(
            loss_stop
        )

        (
            currency,
            fx
        ) = currency_setup(
            currency,
            fx
        )

        try:

            c = connect(d)

            f = get_filters(c)

            # =================================================
            # REAL ACCOUNT BALANCE
            # =================================================

            usdt, btc = balances(c)

            print()

            print(
                GR +
                f'Binance Available USDT: '
                f'${usdt:,.4f}' +
                R
            )

            print(
                CY +
                f'Binance BTC Balance: '
                f'{btc:.8f}' +
                R
            )

            time.sleep(2)

            run_bot(
                c,
                d,
                f,
                mode,
                amount,
                dip,
                target,
                loss_stop,
                currency,
                fx
            )

        except Exception as e:

            print()

            print(
                RD +
                'Connection/setup error:' +
                R
            )

            print(
                str(e)
            )

            input(
                'Press Enter for menu...'
            )


# ============================================================
# START
# ============================================================

if __name__ == '__main__':

    main()