import pandas as pd
import json
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_writer_profiles():
    try:
        with open('writer_profiles.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("writer_profiles.json missing, using default profile")
        return {
            "default": {
                "name": "ONN Staff",
                "tone": "neutral",
                "expertise": "all",
                "prompt": "Write in a neutral, factual tone, summarizing key data points."
            }
        }

def generate_article(section, df, exchange='AI1', spreadsheet=None, spreadsheet_id='1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI'):
    writer_profiles = load_writer_profiles()
    writer = next((w for w in writer_profiles.values() if section in w['expertise']), writer_profiles['default'])
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Load historical data for trends
    historical_data = pd.DataFrame()
    if spreadsheet:
        try:
            onn_data = pd.DataFrame(spreadsheet.worksheet("ONN_Historical_Data").get_all_records())
            onn_data['Timestamp'] = pd.to_datetime(onn_data['Timestamp'])
            historical_data = onn_data[onn_data['Timestamp'] >= datetime.utcnow() - timedelta(days=7)]
        except Exception as e:
            logger.error(f"Error loading ONN_Historical_Data: {e}")
    
    if section == "Market Watch":
        al_data = historical_data[historical_data['Ticker'] == 'AL'] if not historical_data.empty else pd.DataFrame()
        trend = (al_data['Ask_Price'].iloc[-1] / al_data['Ask_Price'].iloc[0] - 1) if len(al_data) > 1 else 0.0
        max_profit = df['Profit'].max() if not df.empty and 'Profit' in df.columns else 0.0
        top_arb = df.sort_values('Profit', ascending=False).head(1) if not df.empty and 'Profit' in df.columns else pd.DataFrame()
        top_product = top_arb['Product'].iloc[0] if not top_arb.empty else "N/A"
        return f"""# Market Watch: Commodity Price Update
*Reported by {writer['name']}, Cycle {date_str}*

Aluminium prices on the {exchange} exchange show a {trend:.1%} trend over the past 7 days, driven by shifts in industrial demand. {top_product} leads arbitrage opportunities, offering up to ${max_profit:.2f} in potential profit. Traders are advised to monitor supply and demand dynamics closely.

[Read More](#)
"""
    elif section == "Corporate Affairs":
        top_produce = df[df['Recommendation'] == 'Produce'].sort_values('ROI (Ask)', ascending=False).head(1) if not df.empty and 'Recommendation' in df.columns else pd.DataFrame()
        company_product = top_produce['Product'].iloc[0] if not top_produce.empty else "N/A"
        roi = top_produce['ROI (Ask)'].iloc[0] if not top_produce.empty else 0.0
        return f"""# Corporate Affairs: Production Leaders
*Reported by {writer['name']}, Cycle {date_str}*

Corporations focusing on {company_product} report strong performance, with production yielding an estimated ROI of {roi:.2%} on {exchange}. Strategic investments in high-ROI materials are reshaping competitive dynamics in the sector.

[Read More](#)
"""
    elif section == "Politics & Factions":
        top_choke = df.sort_values('Choke_Score', ascending=False).head(1) if not df.empty and 'Choke_Score' in df.columns else pd.DataFrame()
        material = top_choke['Material'].iloc[0] if not top_choke.empty else "N/A"
        choke_score = top_choke['Choke_Score'].iloc[0] if not top_choke.empty else 0.0
        return f"""# Politics & Factions: Resource Control Debates
*Reported by {writer['name']}, Cycle {date_str}*

The Galactic Senate is addressing supply constraints on {material}, a critical resource with a choke score of {choke_score:.2f}. Factions are vying for control, as shortages could impact production across multiple systems.

[Read More](#)
"""
    elif section == "Frontier Reports":
        high_tier = df[df['Tier'] >= 3].sort_values('Investment_Score', ascending=False).head(1) if not df.empty and 'Tier' in df.columns else pd.DataFrame()
        product = high_tier['Product'].iloc[0] if not high_tier.empty else "N/A"
        invest_score = high_tier['Investment_Score'].iloc[0] if not high_tier.empty else 0.0
        return f"""# Frontier Reports: New Colony Developments
*Reported by {writer['name']}, Cycle {date_str}*

A new colony on the outer rim reports promising production of {product}, with an investment score of {invest_score:.2f}. Early assessments suggest significant resource potential, attracting explorer interest.

[Read More](#)
"""
    elif section == "Editorials":
        high_risk = df[df['Risk'] > 0.5].sort_values('Risk', ascending=False).head(1) if not df.empty and 'Risk' in df.columns else pd.DataFrame()
        risk_product = high_risk['Product'].iloc[0] if not high_risk.empty else "N/A"
        risk_score = high_risk['Risk'].iloc[0] if not high_risk.empty else 0.0
        return f"""# Editorial: Strategic Market Insights
*Reported by {writer['name']}, Cycle {date_str}*

Investors should exercise caution with {risk_product}, which carries a high risk score of {risk_score:.2f} due to market volatility. Diversifying into stable, high-ROI materials may offer better returns in the current cycle.

[Read More](#)
"""
    else:
        return f"""# {section}: No Data Available
*Reported by {writer['name']}, Cycle {date_str}*

No significant updates available for this section at this time. Please check back for the latest developments.

[Read More](#)
"""