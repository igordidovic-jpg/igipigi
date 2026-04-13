# CFOS-XG PRO 75 TITAN - Setup Guide

## Overview

This is the **CFOS-XG PRO 75 TITAN** live football analytics and Telegram betting bot system.

### File Structure

```
igipigi/
├── LUCKY-7-92.py            # Core analytics engine (7,773 lines)
├── telegram_bot.py          # Telegram live bot
├── cfos_optimized.py        # Optimized wrapper with caching
├── config.yaml              # Central configuration
├── requirements.txt         # Python dependencies
├── engine/
│   ├── __init__.py
│   ├── lambda_calculator.py # Poisson/lambda calculations
│   ├── momentum_detector.py # Momentum & tempo detection
│   ├── bet_scorer.py        # Bet decision extraction
│   └── monte_carlo.py       # Parallel Monte Carlo engine
├── utils/
│   ├── __init__.py
│   ├── database.py          # SQLite match history
│   ├── cache.py             # Result caching (5-min TTL)
│   └── logging_config.py    # Structured JSON logging
└── tests/
    ├── __init__.py
    ├── test_lambda.py       # Lambda calculator tests
    └── test_bet_scorer.py   # Bet scorer tests
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///cfos.db
WEBHOOK_URL=https://your-domain.com
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram.

### 3. Run the Bot

```bash
python telegram_bot.py
```

### 4. Run Tests

```bash
pytest tests/
```

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and show help |
| `/csv [data]` | Analyze match CSV → get BET DECISION |
| `/live [teams]` | Start live match tracking |
| `/stats` | Your accuracy statistics |
| `/history` | Last 10 match analyses |
| `/alert MODE` | Set alert level: HIGH / MEDIUM / ALL |
| `/language CODE` | Set language: SLO / ENG |

## CSV Format

```
home,away,odds_home,odds_draw,odds_away,minute,score_home,score_away,
xg_home,xg_away,shots_home,shots_away,sot_home,sot_away,
attacks_home,attacks_away,danger_home,danger_away,
big_chances_home,big_chances_away,yellow_home,yellow_away,
red_home,red_away,possession_home,possession_away,
blocked_home,blocked_away,bcm_home,bcm_away,corners_home,corners_away
```

### Example

```
Arsenal,Chelsea,2.10,3.30,3.80,68,1,0,0.80,0.50,6,4,3,2,22,18,8,5,2,1,1,0,0,0,58,42,1,2,0,1,5,3
```

## Sample Bot Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚽ Arsenal vs Chelsea [68']
📊 Score: 1-0
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 BET: NEXT GOAL HOME
🔥 CONFIDENCE: HIGH
⏱️ VALID: 68-73 min
📊 P(GOAL): 72.0%
🎯 MC: 64% / 25% / 11%
━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP 5 ALTERNATIVES:
1️⃣ NEXT GOAL HOME (8.5)
2️⃣ NO BET (7.2)
3️⃣ COMEBACK AWAY (5.8)
4️⃣ DRAW (4.1)
5️⃣ NO GOAL (3.2)
```

## Alert Levels

- **HIGH**: Only send alerts for HIGH confidence bets
- **MEDIUM**: Send alerts for HIGH and MEDIUM confidence bets
- **ALL**: Send alerts for all bets (including LOW confidence)

## Live Tracking

Start tracking a match:
```
/live Arsenal Chelsea
```

Send updates with new data:
```
/live Arsenal,Chelsea,2.10,3.30,3.80,72,1,1,0.95,...
```

Stop tracking:
```
/live stop
```

## Performance Improvements

Compared to the base `LUCKY-7-92.py`:

| Feature | Improvement |
|---------|-------------|
| Result caching | 5x faster for repeated inputs |
| Parallel Monte Carlo | 2x faster simulation |
| Async Telegram bot | 10x user capacity |
| SQLite match history | Full accuracy tracking |

## Configuration

Edit `config.yaml` to customize:

- Simulation parameters (SIM_BASE, SIM_HIGH, SIM_EXTREME)
- Cache TTL and max entries
- Database path
- Alert levels
- Model thresholds (HIGH/MEDIUM confidence)
- Presets (Conservative/Balanced/Aggressive)

## Production Deployment

For webhook mode (faster, recommended for production):

```env
WEBHOOK_URL=https://your-domain.com
PORT=8443
```

The bot will automatically use webhook if `WEBHOOK_URL` is set.
