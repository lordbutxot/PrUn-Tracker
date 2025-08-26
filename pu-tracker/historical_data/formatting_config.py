import pandas as pd

# Color scheme for different performance levels
FORMATTING_CONFIG = {
    'colors': {
        # Performance colors (traffic light system)
        'excellent': {'red': 0.2, 'green': 0.8, 'blue': 0.2},      # Dark green
        'good': {'red': 0.6, 'green': 0.9, 'blue': 0.6},          # Light green
        'neutral': {'red': 1.0, 'green': 1.0, 'blue': 0.8},       # Light yellow
        'poor': {'red': 1.0, 'green': 0.8, 'blue': 0.6},          # Light orange
        'bad': {'red': 0.9, 'green': 0.4, 'blue': 0.4},           # Light red
        'critical': {'red': 0.8, 'green': 0.2, 'blue': 0.2},      # Dark red
        
        # Header colors
        'header_dark': {'red': 0.2, 'green': 0.2, 'blue': 0.2},   # Dark gray
        'header_text': {'red': 1.0, 'green': 1.0, 'blue': 1.0},   # White
        
        # Category colors (for different material types)
        'category_raw': {'red': 0.9, 'green': 0.9, 'blue': 0.7},      # Light brown
        'category_manufactured': {'red': 0.7, 'green': 0.8, 'blue': 0.9}, # Light blue
        'category_consumable': {'red': 0.9, 'green': 0.7, 'blue': 0.9},   # Light purple
        'category_construction': {'red': 0.8, 'green': 0.9, 'blue': 0.7}, # Light green
    },
    
    'thresholds': {
        'roi': {
            'excellent': 50,    # >50% ROI
            'good': 20,         # 20-50% ROI
            'neutral': 5,       # 5-20% ROI
            'poor': 0,          # 0-5% ROI
            'bad': -10,         # -10-0% ROI
            'critical': -999    # <-10% ROI
        },
        'investment_score': {
            'excellent': 8.5,   # >8.5 score
            'good': 7.0,        # 7.0-8.5 score
            'neutral': 5.0,     # 5.0-7.0 score
            'poor': 3.0,        # 3.0-5.0 score
            'bad': 1.5,         # 1.5-3.0 score
            'critical': 0       # <1.5 score
        },
        'risk': {
            'excellent': 3,     # <3 risk (low risk is good)
            'good': 5,          # 3-5 risk
            'neutral': 7,       # 5-7 risk
            'poor': 8.5,        # 7-8.5 risk
            'bad': 9.5,         # 8.5-9.5 risk
            'critical': 999     # >9.5 risk
        },
        'viability': {
            'excellent': 8.5,   # >8.5 viability
            'good': 7.0,        # 7.0-8.5 viability
            'neutral': 5.0,     # 5.0-7.0 viability
            'poor': 3.0,        # 3.0-5.0 viability
            'bad': 1.5,         # 1.5-3.0 viability
            'critical': 0       # <1.5 viability
        }
    }
}

def get_performance_color(value, metric_type):
    """Get color based on performance thresholds."""
    if value is None or pd.isna(value):
        return FORMATTING_CONFIG['colors']['neutral']
    
    thresholds = FORMATTING_CONFIG['thresholds'][metric_type]
    colors = FORMATTING_CONFIG['colors']
    
    if metric_type == 'risk':  # Risk is inverted (lower is better)
        if value <= thresholds['excellent']:
            return colors['excellent']
        elif value <= thresholds['good']:
            return colors['good']
        elif value <= thresholds['neutral']:
            return colors['neutral']
        elif value <= thresholds['poor']:
            return colors['poor']
        elif value <= thresholds['bad']:
            return colors['bad']
        else:
            return colors['critical']
    else:  # ROI, Investment Score, Viability (higher is better)
        if value >= thresholds['excellent']:
            return colors['excellent']
        elif value >= thresholds['good']:
            return colors['good']
        elif value >= thresholds['neutral']:
            return colors['neutral']
        elif value >= thresholds['poor']:
            return colors['poor']
        elif value >= thresholds['bad']:
            return colors['bad']
        else:
            return colors['critical']