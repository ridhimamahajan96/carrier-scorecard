# =============================================================================
# SCORING ENGINE - Sustainability Transport Supplier Scorecard
# Version 2.4 - Updated Carbon Credits scoring
# =============================================================================

import pandas as pd
import re

TIER_WEIGHTS = {1: 3, 2: 2, 3: 1}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_blank(value):
    if value is None:
        return True
    if pd.isna(value):
        return True
    if str(value).strip() == '':
        return True
    return False

def has_numeric(value):
    if is_blank(value):
        return False
    return bool(re.search(r'\d+', str(value)))

def extract_number(value):
    if is_blank(value):
        return None
    v = str(value).lower().strip()
    if v in ['not applicable', 'n/a', 'na', 'nil', '-', 'false', 'true']:
        return 0
    v = v.replace('%', '').replace(',', '')
    try:
        return float(v)
    except:
        nums = re.findall(r'[\d.]+', v)
        if nums:
            try:
                return float(nums[0])
            except:
                pass
    return None

def extract_percentage(value):
    """Extract percentage value from response"""
    if is_blank(value):
        return None
    v = str(value).lower().strip()
    if v in ['not applicable', 'n/a', 'na', 'nil', '-', 'false', 'true', 'not sure']:
        return None
    nums = re.findall(r'(\d+(?:\.\d+)?)\s*%?', v)
    if nums:
        try:
            return float(nums[0])
        except:
            pass
    return None

# =============================================================================
# GENERIC SCORING FUNCTIONS
# =============================================================================

def score_completion_numeric(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower().strip()
    if v in ['not applicable', 'n/a', 'na', 'nil', '-', 'false', 'true']:
        return 0, f"Not Applicable: {value}"
    if v in ['0', '0%', '0.0', '0.00', '0.0%', '0.00%']:
        return 0, "Zero reported"
    if 'e-' in v or 'e+' in v:
        try:
            num_val = float(v.replace('%', ''))
            if abs(num_val) < 0.01:
                return 0, "Zero/negligible reported"
            return 5, f"Numeric: {value}"
        except:
            return 0, f"Invalid: {value}"
    try:
        num_val = float(v.replace('%', '').replace(',', ''))
        if num_val == 0 or abs(num_val) < 0.01:
            return 0, "Zero reported"
        return 5, f"Numeric: {value}"
    except:
        pass
    nums = re.findall(r'[\d.]+', v)
    if nums:
        try:
            num_val = float(nums[0])
            if num_val == 0 or abs(num_val) < 0.01:
                return 0, "Zero reported"
            return 5, f"Numeric: {value}"
        except:
            pass
    return 0, f"No valid numeric: {value}"

def score_completion_text(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower().strip()
    if v in ['false', 'true', 'n/a', 'na', 'not applicable']:
        return 0, f"Invalid response: {value}"
    if len(v) < 3:
        return 0, f"Response too short: {value}"
    return 5, f"Response: {str(value)[:100]}"

def score_unscored(value, **kwargs):
    """Scoring function for unscored questions - always returns 0"""
    return 0, "Unscored - informational only"

# =============================================================================
# TAB 3: EMISSIONS BASELINE SCORING FUNCTIONS
# =============================================================================

def score_tab3_q4(value, **kwargs):
    """Q4: GHG reporting frameworks - Tier 2, not sure = 0 pts"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid framework"
    if any(fw in v for fw in ['ghg protocol', 'sbti', 'glec', 'iso 14083', 'ecotransit']):
        return 5, f"Recognized framework: {value}"
    elif 'internal' in v and 'not sure' not in v and 'none' not in v:
        return 2, "Only Internal Framework"
    elif 'not sure' in v or 'none' in v:
        return 0, "Not sure/None selected - 0 pts"
    return 0, f"No valid framework: {value}"

def score_tab3_q5(value, depends_value=None, **kwargs):
    """Q5: Conditional - 2 pts if Q4='not sure' and explanation provided"""
    if depends_value is None:
        return 0, "Q4 value not available"
    q4_lower = str(depends_value).lower() if depends_value else ''
    if 'not sure' not in q4_lower and 'none' not in q4_lower:
        return 0, "N/A - Q4 was not 'Not sure/None'"
    if is_blank(value):
        return 0, "Q4 was 'Not sure' but no explanation provided"
    v = str(value).lower().strip()
    if v in ['false', 'true', 'n/a', 'na']:
        return 0, "No valid explanation provided"
    if len(v) < 5:
        return 0, "Explanation too short"
    return 2, f"Explanation provided (needs manual review): {str(value)[:100]}"

def score_tab3_q6(value, **kwargs):
    """Q6: Emissions reporting boundary - Tier 2, not sure = 0 pts"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid boundary"
    has_valid = any(opt in v for opt in ['ttw', 'wtw', 'wtt', 'tank to wheel', 'well to wheel', 'well to tank'])
    has_wtw = 'wtw' in v or 'well to wheel' in v
    if 'not sure' in v and not has_valid:
        return 0, "Not sure selected - 0 pts"
    elif has_valid:
        score = 5 + (2 if has_wtw else 0)
        return score, f"Valid boundary: {value}" + (" (+2 WTW bonus)" if has_wtw else "")
    return 0, f"No valid boundary: {value}"

def score_tab3_q7(value, **kwargs):
    """Q7: Unit for reporting - Tier 2, CO2e=5, CO2=3, Both=5"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid response"
    if 'both' in v:
        return 5, f"Both selected: {value}"
    if 'co2e' in v or 'co2 e' in v or 'co2-e' in v:
        return 5, f"CO2e selected: {value}"
    if 'co2' in v:
        return 3, f"CO2 only selected: {value}"
    return 0, f"No valid unit: {value}"

def score_tab3_q8(value, **kwargs):
    """Q8: Scopes included - Tier 1"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No scopes identified"
    count = 0
    if 'scope 1' in v or 'scope1' in v:
        count += 1
    if 'scope 2' in v or 'scope2' in v:
        count += 1
    if 'scope 3' in v or 'scope3' in v:
        count += 1
    if count == 3:
        return 5, f"All 3 scopes: {value}"
    elif count == 2:
        return 4, f"2 scopes: {value}"
    elif count == 1:
        return 3, f"1 scope: {value}"
    return 0, f"No scopes identified: {value}"

# =============================================================================
# TAB 4: REDUCTION TARGETS SCORING FUNCTIONS
# =============================================================================

def score_tab4_q1(value, **kwargs):
    """Q1: Carbon neutrality goal - No = 0 pts"""
    if is_blank(value):
        return 0, "Blank response - 0 pts"
    v = str(value).lower().strip()
    if v == 'yes':
        return 5, "Yes - has carbon neutrality goal"
    elif 'development' in v or 'in progress' in v:
        return 2, "In development"
    elif v == 'no':
        return 0, "No carbon neutrality goal - 0 pts"
    return 0, f"Unrecognized: {value}"

def score_tab4_q2(value, **kwargs):
    """Q2: Target year"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value)
    if '2030' in v and '2031' not in v:
        return 5, "Target: 2030"
    elif '2031-2040' in v or '2031' in v or '2035' in v or '2040' in v:
        return 4, f"Target: 2031-2040 ({value})"
    elif '2041-2050' in v or '2045' in v:
        return 3, f"Target: 2041-2050 ({value})"
    elif '2050' in v and 'beyond' not in v.lower():
        return 2, "Target: 2050"
    elif 'beyond' in v.lower():
        return 1, "Target: Beyond 2050"
    return 0, f"Could not determine: {value}"

def score_tab4_q3_curve(value, **kwargs):
    """Q3: Company level emissions reduction by 2030 - Tier 2, graded curve"""
    if is_blank(value):
        return 0, "Blank response - 0 pts", None
    
    v = str(value).lower().strip()
    if v in ['not sure', 'n/a', 'na', 'false', 'true']:
        return 0, "Not sure/No answer - 0 pts", None
    
    pct = extract_percentage(value)
    
    if pct is None:
        return 0, f"Could not extract percentage from: {value}", None
    
    justification = f"Reported {pct}% reduction target - PENDING CURVE ADJUSTMENT (Manual review required)"
    return 3, justification, pct

def score_tab4_q4_conditional(value, depends_value=None, **kwargs):
    """Q4: Estimate if Q3='not sure' - ONLY SCORES IF Q3 = 'not sure'"""
    if depends_value is None:
        return 0, "N/A - Q3 value not available"
    
    q3_lower = str(depends_value).lower().strip()
    if 'not sure' not in q3_lower:
        return 0, "N/A - Q3 was not 'Not sure' (Q4 only scored when Q3 = Not sure)"
    
    if is_blank(value):
        return 0, "Q3 was 'Not sure' but no estimate provided in Q4 (Manual review required)"
    
    v = str(value).lower().strip()
    if v in ['false', 'true', 'n/a', 'na']:
        return 0, "No valid response provided (Manual review required)"
    
    has_number = bool(re.search(r'\d+', v))
    has_year = bool(re.search(r'20\d{2}', v))
    has_percentage = '%' in v or 'percent' in v
    
    if has_number and has_year:
        return 5, f"Clear goal with year stated: {value} (Manual review required)"
    elif has_number and has_percentage:
        return 4, f"Goal stated with percentage: {value} (Manual review required)"
    elif has_number:
        return 3, f"Numeric goal stated: {value} (Manual review required)"
    else:
        return 2, f"Goal described but not quantified: {value} (Manual review required)"

def score_tab4_q5a_curve(value, **kwargs):
    """Q5a: Apple specific overall emissions reduction - Tier 1, graded curve"""
    if is_blank(value):
        return 0, "Blank response - 0 pts", None
    
    v = str(value).lower().strip()
    if v in ['not sure', 'n/a', 'na', 'false', 'true', '0', '0%']:
        return 0, "No reduction target - 0 pts", None
    
    pct = extract_percentage(value)
    
    if pct is None:
        return 0, f"Could not extract percentage from: {value}", None
    
    if pct == 0:
        return 0, "0% reduction target - 0 pts", 0
    
    justification = f"Reported {pct}% Apple-specific reduction - PENDING CURVE ADJUSTMENT (Manual review required)"
    return 3, justification, pct

def score_tab4_q5_scope(value, **kwargs):
    """Q5b/c/d: Apple scope breakdown - Tier 2"""
    if is_blank(value):
        return 0, "Blank response", None
    
    v = str(value).lower().strip()
    if v in ['not sure', 'n/a', 'na', 'false', 'true']:
        return 0, "No value provided", None
    
    pct = extract_percentage(value)
    
    if pct is None:
        return 0, f"Could not extract percentage: {value}", None
    
    return 5, f"Scope reduction: {pct}%", pct

def validate_q5_scope_totals(q5a_val, q5b_val, q5c_val, q5d_val):
    """Validate that Q5b+Q5c+Q5d scope breakdowns align with Q5a overall"""
    q5a_pct = extract_percentage(q5a_val)
    q5b_pct = extract_percentage(q5b_val)
    q5c_pct = extract_percentage(q5c_val)
    q5d_pct = extract_percentage(q5d_val)
    
    scope_values = [q5b_pct, q5c_pct, q5d_pct]
    valid_scopes = [v for v in scope_values if v is not None]
    
    if q5a_pct is None:
        return True, "Q5a not provided - cannot validate"
    
    if len(valid_scopes) == 0:
        return True, "No scope breakdowns provided - cannot validate"
    
    if len(valid_scopes) < 3:
        return False, f"Incomplete scope data: only {len(valid_scopes)}/3 scopes provided"
    
    scope_avg = sum(valid_scopes) / len(valid_scopes)
    
    if q5a_pct > 0:
        variance = abs(scope_avg - q5a_pct) / q5a_pct * 100
        if variance > 50:
            return False, f"Scope breakdown avg ({scope_avg:.1f}%) differs significantly from overall ({q5a_pct}%) - {variance:.1f}% variance"
    
    return True, f"Scope breakdown validates: avg {scope_avg:.1f}% vs overall {q5a_pct}%"

def score_tab4_q6(value, **kwargs):
    """Q6: YoY ramp plan"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value)
    years = sum(1 for y in ['2026', '2027', '2028', '2029', '2030'] if y in v)
    if years >= 4:
        return 5, f"Comprehensive ramp plan"
    elif years >= 1:
        return 2, f"Partial plan ({years} years)"
    nums = re.findall(r'(\d+)', v)
    if nums:
        return 5, f"Ramp plan provided: {value}"
    return 0, "No ramp plan identified"

# =============================================================================
# TAB 5: CARBON CREDITS SCORING FUNCTIONS (UPDATED)
# =============================================================================

def score_tab5_q1(value, **kwargs):
    """Q1: Carbon credits in strategy - No = 0 pts, Blank = 0 pts"""
    if is_blank(value):
        return 0, "Blank response - 0 pts"
    v = str(value).lower().strip()
    if v == 'yes':
        return 5, "Yes - carbon credits in strategy"
    elif 'development' in v or 'in progress' in v:
        return 3, "In development"
    elif v == 'no':
        return 0, "No carbon credits strategy - 0 pts"
    return 0, f"Unrecognized response: {value} - 0 pts"

def score_tab5_q2(value, **kwargs):
    """Q2: Credit instruments"""
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid instruments"
    recognized = ['nature-based', 'nature based', 'voluntary', 'regulatory', 'compliance']
    if any(r in v for r in recognized):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 2, "Only Others"
    return 0, f"No valid instruments: {value}"

def score_tab5_q4_quality(value, **kwargs):
    """Q4: Quality of credits - Auto 5 if text provided, 0 if blank, flag for manual review"""
    if is_blank(value):
        return 0, "No response provided - 0 pts (Manual review required)"
    
    v = str(value).lower().strip()
    if v in ['false', 'true', 'n/a', 'na', 'not applicable']:
        return 0, f"Invalid response: {value} - 0 pts (Manual review required)"
    
    if len(v) < 5:
        return 0, f"Response too short - 0 pts (Manual review required)"
    
    # Quality check keywords
    quality_keywords = ['gold standard', 'verra', 'verified', 'certified', 'third-party', 
                       'third party', 'iso', 'registry', 'standard', 'accredited', 
                       'audited', 'validation', 'verification', 'quality', 'premium']
    
    has_quality_indicator = any(kw in v for kw in quality_keywords)
    
    if has_quality_indicator:
        return 5, f"Quality indicators found - 5 pts (Manual review required): {str(value)[:100]}"
    else:
        return 5, f"Text response provided - 5 pts (Manual review required to verify quality): {str(value)[:100]}"

def score_tab5_q5_approach(value, **kwargs):
    """Q5: Near-term approach - Auto 5 if text provided, 0 if blank, flag for manual review"""
    if is_blank(value):
        return 0, "No response provided - 0 pts (Manual review required)"
    
    v = str(value).lower().strip()
    if v in ['false', 'true', 'n/a', 'na', 'not applicable']:
        return 0, f"Invalid response: {value} - 0 pts (Manual review required)"
    
    if len(v) < 5:
        return 0, f"Response too short - 0 pts (Manual review required)"
    
    # Approach quality keywords
    approach_keywords = ['reduce', 'reduction', 'offset', 'invest', 'purchase', 'retire',
                        'transition', 'phase', 'timeline', 'plan', 'strategy', 'goal',
                        'target', 'commit', 'renewable', 'sustainable', 'decarbonize']
    
    has_approach_indicator = any(kw in v for kw in approach_keywords)
    
    if has_approach_indicator:
        return 5, f"Clear approach described - 5 pts (Manual review required): {str(value)[:100]}"
    else:
        return 5, f"Text response provided - 5 pts (Manual review required to verify approach): {str(value)[:100]}"

def score_conditional_text(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent value not available"
    if condition and condition.lower() not in str(depends_value).lower():
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, "No explanation provided"
    v = str(value).lower()
    if v in ['false', 'true', 'na', 'n/a']:
        return 0, "No explanation provided"
    return 3, f"Explanation provided: {str(value)[:50]}"

def score_conditional_text_2pts(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent value not available"
    if condition and condition.lower() not in str(depends_value).lower():
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, "No explanation provided"
    v = str(value).lower()
    if v in ['false', 'true', 'na', 'n/a']:
        return 0, "No explanation provided"
    return 2, f"Explanation provided: {str(value)[:50]}"

# =============================================================================
# TAB 6: AIR FREIGHT SCORING FUNCTIONS
# =============================================================================

def score_tab6_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid strategy"
    if 'saf' in v or 'sustainable aviation fuel' in v:
        return 5, f"SAF selected: {value}"
    elif any(r in v for r in ['fleet', 'route', 'payload', 'load factor', 'modernisation', 'modernization', 'optimisation', 'optimization']):
        return 3, f"Recognized strategy: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid strategy: {value}"

# =============================================================================
# TAB 7: OCEAN FREIGHT SCORING FUNCTIONS
# =============================================================================

def score_tab7_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid strategy"
    if any(r in v for r in ['alternative fuel', 'vessel efficiency', 'route', 'slow steaming', 'optimisation', 'optimization']):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid strategy: {value}"

def score_tab7_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid fuel"
    if any(r in v for r in ['lng', 'methanol', 'ammonia', 'bio-lng', 'e-lng', 'bio-methanol', 'e-methanol']):
        return 5, f"Recognized fuel: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid fuel: {value}"

# =============================================================================
# TAB 8: GROUND FREIGHT SCORING FUNCTIONS
# =============================================================================

def score_tab8_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid strategy"
    if any(r in v for r in ['electric', 'bev', 'hybrid', 'alternative fuel', 'biofuel', 'route', 'load', 'ev']):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid strategy: {value}"

def score_tab8_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'false' in v or v == 'true':
        return 0, "No valid fuel"
    if any(r in v for r in ['biofuel', 'renewable diesel', 'rng', 'hvo', 'biodiesel', 'hydrogen', 'fuel cell', 'bio-cng', 'bio-lng']):
        return 5, f"Recognized fuel: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid fuel: {value}"

# =============================================================================
# SCORING RULES CONFIGURATION
# =============================================================================

def get_scoring_rules():
    return {
        'tab3': {'name': 'Emissions Baseline', 'section': 2, 'questions': {
            'Q4': {
                'description': 'GHG reporting frameworks',
                'tier': 2,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab3_q4,
                'is_checkbox': True
            },
            'Q5': {
                'description': 'Explain if Not sure/None',
                'tier': 3,
                'max_pts': 2,
                'manual_review': True,
                'review_criteria': 'Verify explanation of GHG framework approach',
                'score_func': score_tab3_q5,
                'depends_on': 'Q4'
            },
            'Q6': {
                'description': 'Emissions reporting boundary',
                'tier': 2,
                'max_pts': 7,
                'manual_review': False,
                'score_func': score_tab3_q6,
                'is_checkbox': True
            },
            'Q7': {
                'description': 'Unit for reporting',
                'tier': 2,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab3_q7,
                'is_checkbox': True
            },
            'Q8': {
                'description': 'Scopes included',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab3_q8,
                'is_checkbox': True
            },
            'Q9': {
                'description': 'Company total GHG FY2025',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_total': True,
                'total_group': 'company'
            },
            'Q10': {
                'description': 'Company Scope 1',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_scope': True,
                'total_group': 'company'
            },
            'Q11': {
                'description': 'Company Scope 2',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_scope': True,
                'total_group': 'company'
            },
            'Q12': {
                'description': 'Company Scope 3',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_scope': True,
                'total_group': 'company'
            },
            'Q13': {
                'description': 'Apple total emissions',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_total': True,
                'total_group': 'apple'
            },
            'Q14': {
                'description': 'Apple Scope 1',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_scope': True,
                'total_group': 'apple'
            },
            'Q15': {
                'description': 'Apple Scope 2',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_scope': True,
                'total_group': 'apple'
            },
            'Q16': {
                'description': 'Apple Scope 3',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_numeric,
                'is_scope': True,
                'total_group': 'apple'
            },
            'Q17': {
                'description': 'Methodology for allocation',
                'tier': 3,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_text
            },
            'Q18': {
                'description': 'Allocation methodology details',
                'tier': None,
                'max_pts': 0,
                'manual_review': False,
                'score_func': score_unscored,
                'unscored': True
            },
            'Q19': {
                'description': 'Third-party verification',
                'tier': 3,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_completion_text
            },
            'Q20': {
                'description': 'Verification details',
                'tier': None,
                'max_pts': 0,
                'manual_review': False,
                'score_func': score_unscored,
                'unscored': True
            },
        }},
        
        'tab4': {'name': 'Reduction Targets', 'section': 3, 'questions': {
            'Q1': {
                'description': 'Carbon neutrality goal',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab4_q1
            },
            'Q2': {
                'description': 'Target year',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab4_q2
            },
            'Q3': {
                'description': 'Company reduction by FY2030',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review company reduction target - Graded curve applies',
                'score_func': score_tab4_q3_curve,
                'is_curve': True
            },
            'Q4': {
                'description': 'Reduction goal estimate (if Q3=Not sure)',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Verify clear number goal with year (only scored if Q3=Not sure)',
                'score_func': score_tab4_q4_conditional,
                'depends_on': 'Q3'
            },
            'Q5a': {
                'description': 'Apple overall reduction FY2030',
                'tier': 1,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review Apple-specific reduction target - Graded curve applies',
                'score_func': score_tab4_q5a_curve,
                'is_sub_row': True,
                'sub_row_text': 'overall',
                'is_curve': True
            },
            'Q5b': {
                'description': 'Apple Scope 1 reduction FY2030',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Validate scope breakdown matches overall',
                'score_func': score_tab4_q5_scope,
                'is_sub_row': True,
                'sub_row_text': 'scope 1',
                'is_scope_breakdown': True
            },
            'Q5c': {
                'description': 'Apple Scope 2 reduction FY2030',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Validate scope breakdown matches overall',
                'score_func': score_tab4_q5_scope,
                'is_sub_row': True,
                'sub_row_text': 'scope 2',
                'is_scope_breakdown': True
            },
            'Q5d': {
                'description': 'Apple Scope 3 reduction FY2030',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Validate scope breakdown matches overall',
                'score_func': score_tab4_q5_scope,
                'is_sub_row': True,
                'sub_row_text': 'scope 3',
                'is_scope_breakdown': True
            },
            'Q6': {
                'description': 'YoY ramp plan',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab4_q6,
                'is_checkbox': True
            },
        }},
        
        # =====================================================================
        # TAB 5: CARBON CREDITS (Section 4) - UPDATED
        # =====================================================================
        'tab5': {'name': 'Carbon Credits', 'section': 4, 'questions': {
            'Q1': {
                'description': 'Carbon credits in strategy',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab5_q1
            },
            'Q2': {
                'description': 'Credit instruments',
                'tier': 2,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab5_q2,
                'is_checkbox': True
            },
            'Q3': {
                'description': 'Explain Others',
                'tier': 3,
                'max_pts': 3,
                'manual_review': True,
                'review_criteria': 'Verify strategy explanation',
                'score_func': score_conditional_text,
                'depends_on': 'Q2',
                'condition': 'Others'
            },
            'Q4': {
                'description': 'Quality of credits',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Verify quality standards and certifications mentioned',
                'score_func': score_tab5_q4_quality
            },
            'Q5': {
                'description': 'Near-term approach',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Verify near-term carbon credit strategy is clear and actionable',
                'score_func': score_tab5_q5_approach
            },
        }},
        
        'tab6': {'name': 'Air Freight', 'section': 5, 'conditional': 'Air', 'questions': {
            'Q1': {
                'description': 'Air strategies',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab6_q1,
                'is_checkbox': True
            },
            'Q2': {
                'description': 'Explain Others',
                'tier': 3,
                'max_pts': 2,
                'manual_review': True,
                'review_criteria': 'Verify',
                'score_func': score_conditional_text_2pts,
                'depends_on': 'Q1',
                'condition': 'Others'
            },
            'Q3': {
                'description': 'SAF strategy',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review SAF',
                'score_func': score_completion_text
            },
            'Q4': {
                'description': 'Apple SAF strategy',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review Apple SAF',
                'score_func': score_completion_text
            },
        }},
        
        'tab7': {'name': 'Ocean Freight', 'section': 6, 'conditional': 'Ocean', 'questions': {
            'Q1': {
                'description': 'Ocean strategies',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab7_q1,
                'is_checkbox': True
            },
            'Q2': {
                'description': 'Explain Others',
                'tier': 3,
                'max_pts': 2,
                'manual_review': True,
                'review_criteria': 'Verify',
                'score_func': score_conditional_text_2pts,
                'depends_on': 'Q1',
                'condition': 'Others'
            },
            'Q3': {
                'description': 'Alternative fuels',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab7_q3,
                'is_checkbox': True
            },
            'Q4': {
                'description': 'Explain Others fuels',
                'tier': 3,
                'max_pts': 2,
                'manual_review': True,
                'review_criteria': 'Verify',
                'score_func': score_conditional_text_2pts,
                'depends_on': 'Q3',
                'condition': 'Others'
            },
            'Q5': {
                'description': 'Company fuel strategy',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review',
                'score_func': score_completion_text
            },
            'Q6': {
                'description': 'Apple ocean strategy',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review',
                'score_func': score_completion_text
            },
        }},
        
        'tab8': {'name': 'Ground Freight', 'section': 7, 'conditional': 'Ground', 'questions': {
            'Q1': {
                'description': 'Ground strategies',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab8_q1,
                'is_checkbox': True
            },
            'Q2': {
                'description': 'Explain Others',
                'tier': 3,
                'max_pts': 2,
                'manual_review': True,
                'review_criteria': 'Verify',
                'score_func': score_conditional_text_2pts,
                'depends_on': 'Q1',
                'condition': 'Others'
            },
            'Q3': {
                'description': 'Alternative fuels',
                'tier': 1,
                'max_pts': 5,
                'manual_review': False,
                'score_func': score_tab8_q3,
                'is_checkbox': True
            },
            'Q4': {
                'description': 'Explain Others fuels',
                'tier': 3,
                'max_pts': 2,
                'manual_review': True,
                'review_criteria': 'Verify',
                'score_func': score_conditional_text_2pts,
                'depends_on': 'Q3',
                'condition': 'Others'
            },
            'Q5': {
                'description': 'Company EV strategy',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review',
                'score_func': score_completion_text
            },
            'Q6': {
                'description': 'Apple ground strategy',
                'tier': 2,
                'max_pts': 5,
                'manual_review': True,
                'review_criteria': 'Review',
                'score_func': score_completion_text
            },
        }}
    }

# =============================================================================
# EXCEL EXTRACTION FUNCTIONS
# =============================================================================

def detect_services(sheets):
    services = set()
    for name, df in sheets.items():
        s = df.to_string().lower()
        if 'air' in s:
            services.add('Air')
        if 'ocean' in s or 'sea' in s:
            services.add('Ocean')
        if 'ground' in s or 'road' in s or 'truck' in s:
            services.add('Ground')
    return services if services else {'Air', 'Ocean', 'Ground'}

def find_sheet_for_tab(sheets, tab_name, section_num):
    for name, df in sheets.items():
        name_lower = name.lower()
        if tab_name.lower().split()[0] in name_lower:
            return df
        if f'section {section_num}' in name_lower:
            return df
        if f'section{section_num}' in name_lower:
            return df
    sheet_list = list(sheets.values())
    return sheet_list[section_num] if section_num < len(sheet_list) else None

def find_response_column(df):
    for idx, col in enumerate(df.columns):
        col_str = str(col).lower()
        if 'response' in col_str or 'your response' in col_str:
            return idx
    if len(df.columns) > 2:
        return 2
    return None

def extract_checkbox_values(df, start_idx, response_col):
    selected = []
    idx = start_idx + 1
    while idx < len(df):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        if col_a.upper().startswith('Q') and len(col_a) <= 4:
            if col_a[1:].replace('a','').replace('b','').replace('c','').replace('d','').isdigit():
                break
        if len(row) > response_col:
            col_b = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            col_resp = row.iloc[response_col] if pd.notna(row.iloc[response_col]) else None
            if col_b and 'check box' not in col_b.lower() and 'select' not in col_b.lower() and len(col_b) > 2:
                if col_resp is not None:
                    resp_str = str(col_resp).strip().lower()
                    is_checked = resp_str in ['true', '1', 'x', '✓', '☑', 'yes'] or (isinstance(col_resp, bool) and col_resp)
                    if is_checked:
                        selected.append(col_b)
        idx += 1
    return ', '.join(selected) if selected else None

def extract_sub_row_value(df, start_idx, sub_text, response_col):
    idx = start_idx + 1
    while idx < len(df):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        if col_a.upper().startswith('Q') and len(col_a) <= 4:
            break
        if len(row) > response_col:
            col_b = str(row.iloc[1]).strip().lower() if pd.notna(row.iloc[1]) else ''
            if sub_text.lower() in col_b:
                col_resp = row.iloc[response_col]
                if pd.notna(col_resp) and str(col_resp).strip():
                    return str(col_resp).strip()
        idx += 1
    return None

def extract_ramp_plan_values(df, start_idx, response_col):
    values = {}
    idx = start_idx + 1
    while idx < len(df):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        if col_a.upper().startswith('Q') and col_a[1:].isdigit():
            break
        if len(row) > response_col:
            col_b = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            col_resp = str(row.iloc[response_col]).strip() if pd.notna(row.iloc[response_col]) else ''
            for year in ['2026', '2027', '2028', '2029', '2030']:
                if year in col_b and col_resp and col_resp.lower() not in ['false', 'true', '']:
                    values[year] = col_resp
        idx += 1
    if values:
        return ', '.join([f"{k}: {v}" for k, v in values.items()])
    return None

def extract_question_value(df, question_key, q_rules=None):
    if df is None:
        return None
    
    q_num = question_key.replace('Q', '').replace('a', '').replace('b', '').replace('c', '').replace('d', '')
    is_checkbox = q_rules.get('is_checkbox', False) if q_rules else False
    is_sub_row = q_rules.get('is_sub_row', False) if q_rules else False
    sub_row_text = q_rules.get('sub_row_text', '') if q_rules else ''
    
    response_col = find_response_column(df)
    if response_col is None:
        response_col = 2
    
    for idx, row in df.iterrows():
        col_a = str(row.iloc[0]).strip().upper() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        
        if col_a == f'Q{q_num}':
            if is_checkbox:
                result = extract_checkbox_values(df, idx, response_col)
                if result:
                    return result
            elif is_sub_row and sub_row_text:
                result = extract_sub_row_value(df, idx, sub_row_text, response_col)
                if result:
                    return result
            elif question_key == 'Q6' and q_rules and 'ramp' in q_rules.get('description', '').lower():
                result = extract_ramp_plan_values(df, idx, response_col)
                if result:
                    return result
            
            if len(row) > response_col:
                col_resp = row.iloc[response_col]
                if pd.notna(col_resp):
                    val = str(col_resp).strip()
                    if val and val.lower() not in ['check boxes that apply', 'check box', 'select', 'select one', 'select all']:
                        return val
    return None

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_scope_totals(sheet, results, carrier):
    """Validate that scope breakdowns total to reported total emissions"""
    manual_items = []
    
    def get_val(q_key):
        val = results.get(q_key, {}).get('value', '')
        return extract_number(val)
    
    q9_val = get_val('Q9')
    q10_val = get_val('Q10')
    q11_val = get_val('Q11')
    q12_val = get_val('Q12')
    
    if q9_val is not None and q9_val > 0:
        scope_vals = [q10_val, q11_val, q12_val]
        if all(v is not None for v in scope_vals):
            scope_sum = sum(v for v in scope_vals)
            likely_percentages = all(v <= 100 for v in scope_vals) and scope_sum <= 150
            
            if likely_percentages:
                variance = abs(scope_sum - 100)
                if variance > 5:
                    manual_items.append({
                        'tab': 'Emissions Baseline',
                        'question': 'Q9-Q12',
                        'description': 'Company scope breakdown validation (percentages)',
                        'value': f"Q9 Total: {q9_val}, Scope1: {q10_val}%, Scope2: {q11_val}%, Scope3: {q12_val}%, Sum: {scope_sum}%",
                        'current_score': 0,
                        'max_score': 0,
                        'review_criteria': 'Scope percentages (Q10+Q11+Q12) should total to 100%',
                        'justification': f'Scope sum ({scope_sum:.1f}%) does not equal 100% (variance: {variance:.1f}%) - needs review',
                        'severity': 'warning'
                    })
            else:
                variance_pct = abs(scope_sum - q9_val) / q9_val * 100 if q9_val > 0 else 0
                if variance_pct > 5:
                    manual_items.append({
                        'tab': 'Emissions Baseline',
                        'question': 'Q9-Q12',
                        'description': 'Company scope breakdown validation (absolute)',
                        'value': f"Q9 Total: {q9_val:,.0f}, Scope1: {q10_val:,.0f}, Scope2: {q11_val:,.0f}, Scope3: {q12_val:,.0f}, Sum: {scope_sum:,.0f}",
                        'current_score': 0,
                        'max_score': 0,
                        'review_criteria': 'Scope values (Q10+Q11+Q12) should total to Q9',
                        'justification': f'Scope sum ({scope_sum:,.0f}) does not equal total ({q9_val:,.0f}) - {variance_pct:.1f}% variance - needs review',
                        'severity': 'warning'
                    })
    
    q13_val = get_val('Q13')
    q14_val = get_val('Q14')
    q15_val = get_val('Q15')
    q16_val = get_val('Q16')
    
    if q13_val is not None and q13_val > 0:
        apple_scope_vals = [q14_val, q15_val, q16_val]
        if all(v is not None for v in apple_scope_vals):
            apple_scope_sum = sum(v for v in apple_scope_vals)
            likely_percentages = all(v <= 100 for v in apple_scope_vals) and apple_scope_sum <= 150
            
            if likely_percentages:
                variance = abs(apple_scope_sum - 100)
                if variance > 5:
                    manual_items.append({
                        'tab': 'Emissions Baseline',
                        'question': 'Q13-Q16',
                        'description': 'Apple scope breakdown validation (percentages)',
                        'value': f"Q13 Total: {q13_val}, Scope1: {q14_val}%, Scope2: {q15_val}%, Scope3: {q16_val}%, Sum: {apple_scope_sum}%",
                        'current_score': 0,
                        'max_score': 0,
                        'review_criteria': 'Apple scope percentages (Q14+Q15+Q16) should total to 100%',
                        'justification': f'Scope sum ({apple_scope_sum:.1f}%) does not equal 100% (variance: {variance:.1f}%) - needs review',
                        'severity': 'warning'
                    })
            else:
                variance_pct = abs(apple_scope_sum - q13_val) / q13_val * 100 if q13_val > 0 else 0
                if variance_pct > 5:
                    manual_items.append({
                        'tab': 'Emissions Baseline',
                        'question': 'Q13-Q16',
                        'description': 'Apple scope breakdown validation (absolute)',
                        'value': f"Q13 Total: {q13_val:,.0f}, Scope1: {q14_val:,.0f}, Scope2: {q15_val:,.0f}, Scope3: {q16_val:,.0f}, Sum: {apple_scope_sum:,.0f}",
                        'current_score': 0,
                        'max_score': 0,
                        'review_criteria': 'Apple scope values (Q14+Q15+Q16) should total to Q13',
                        'justification': f'Scope sum ({apple_scope_sum:,.0f}) does not equal total ({q13_val:,.0f}) - {variance_pct:.1f}% variance - needs review',
                        'severity': 'warning'
                    })
    
    if q13_val and q9_val and q13_val > q9_val:
        manual_items.append({
            'tab': 'Emissions Baseline',
            'question': 'Q13 vs Q9',
            'description': 'Apple vs Company total comparison',
            'value': f"Apple total: {q13_val:,.0f}, Company total: {q9_val:,.0f}",
            'current_score': 0,
            'max_score': 0,
            'review_criteria': 'Apple-specific emissions should not exceed total company emissions',
            'justification': f'Apple emissions ({q13_val:,.0f}) exceed company total ({q9_val:,.0f}) - likely data error',
            'severity': 'error'
        })
    
    return manual_items

def validate_q5_reduction_scopes(results, carrier):
    """Validate Q5b+Q5c+Q5d scope breakdowns against Q5a overall"""
    manual_items = []
    
    def get_val(q_key):
        return results.get(q_key, {}).get('value', '')
    
    q5a_val = get_val('Q5a')
    q5b_val = get_val('Q5b')
    q5c_val = get_val('Q5c')
    q5d_val = get_val('Q5d')
    
    is_valid, message = validate_q5_scope_totals(q5a_val, q5b_val, q5c_val, q5d_val)
    
    if not is_valid:
        manual_items.append({
            'tab': 'Reduction Targets',
            'question': 'Q5a-Q5d',
            'description': 'Apple reduction scope breakdown validation',
            'value': f"Overall: {q5a_val}, Scope1: {q5b_val}, Scope2: {q5c_val}, Scope3: {q5d_val}",
            'current_score': 0,
            'max_score': 0,
            'review_criteria': 'Scope reduction breakdowns should align with overall reduction target',
            'justification': message,
            'severity': 'warning'
        })
    
    return manual_items

# =============================================================================
# MAIN SCORING FUNCTIONS
# =============================================================================

def score_tab(sheets, tab_key, tab_rules, all_rules):
    tab_results = {
        'name': tab_rules['name'],
        'section': tab_rules['section'],
        'questions': {},
        'raw_score': 0,
        'weighted_score': 0,
        'max_raw': 0,
        'max_weighted': 0,
        'manual_review_items': [],
        'curve_data': {}
    }
    
    sheet = find_sheet_for_tab(sheets, tab_rules['name'], tab_rules['section'])
    if sheet is None:
        return tab_results
    
    for q_key, q_rules in tab_rules['questions'].items():
        value = extract_question_value(sheet, q_key, q_rules)
        
        depends_value = None
        if 'depends_on' in q_rules:
            depends_q_rules = tab_rules['questions'].get(q_rules['depends_on'], {})
            depends_value = extract_question_value(sheet, q_rules['depends_on'], depends_q_rules)
        
        condition = q_rules.get('condition')
        
        if 'depends_on' in q_rules:
            result = q_rules['score_func'](value, depends_value=depends_value, condition=condition)
        else:
            result = q_rules['score_func'](value)
        
        if isinstance(result, tuple) and len(result) == 3:
            score, justification, curve_value = result
            if curve_value is not None:
                tab_results['curve_data'][q_key] = curve_value
        else:
            score, justification = result
        
        tier = q_rules.get('tier')
        is_unscored = q_rules.get('unscored', False) or tier is None
        
        if is_unscored:
            weighted = 0
            max_weighted = 0
        else:
            weighted = score * TIER_WEIGHTS[tier]
            max_weighted = q_rules['max_pts'] * TIER_WEIGHTS[tier]
        
        tab_results['questions'][q_key] = {
            'description': q_rules['description'],
            'tier': tier,
            'raw_score': score,
            'max_pts': q_rules['max_pts'],
            'weighted_score': weighted,
            'max_weighted': max_weighted,
            'justification': justification,
            'value': str(value)[:200] if value else '',
            'manual_review': q_rules.get('manual_review', False),
            'unscored': is_unscored,
            'is_curve': q_rules.get('is_curve', False)
        }
        
        if not is_unscored:
            tab_results['raw_score'] += score
            tab_results['weighted_score'] += weighted
            tab_results['max_raw'] += q_rules['max_pts']
            tab_results['max_weighted'] += max_weighted
        
        if q_rules.get('manual_review'):
            tab_results['manual_review_items'].append({
                'tab': tab_rules['name'],
                'question': q_key,
                'description': q_rules['description'],
                'value': str(value)[:500] if value else '',
                'current_score': score,
                'max_score': q_rules['max_pts'],
                'review_criteria': q_rules.get('review_criteria', 'Review'),
                'justification': justification,
                'is_curve': q_rules.get('is_curve', False)
            })
    
    return tab_results

def score_carrier(excel_file, carrier_name=None):
    """Main entry point: Score a carrier's survey responses"""
    try:
        xlsx = pd.ExcelFile(excel_file)
        sheets = {s: pd.read_excel(xlsx, sheet_name=s) for s in xlsx.sheet_names}
    except Exception as e:
        return {'error': str(e)}
    
    services = detect_services(sheets)
    rules = get_scoring_rules()
    
    results = {
        'carrier_name': carrier_name or 'Unknown',
        'services': services,
        'service_type': '+'.join(sorted(services)),
        'tabs': {},
        'manual_review_items': [],
        'total_raw': 0,
        'total_weighted': 0,
        'max_raw': 0,
        'max_weighted': 0,
        'curve_data': {}
    }
    
    for tab_key, tab_rules in rules.items():
        if 'conditional' in tab_rules and tab_rules['conditional'] not in services:
            continue
        
        tab_results = score_tab(sheets, tab_key, tab_rules, rules)
        results['tabs'][tab_key] = tab_results
        results['total_raw'] += tab_results['raw_score']
        results['total_weighted'] += tab_results['weighted_score']
        results['max_raw'] += tab_results['max_raw']
        results['max_weighted'] += tab_results['max_weighted']
        results['manual_review_items'].extend(tab_results['manual_review_items'])
        
        if tab_results.get('curve_data'):
            results['curve_data'][tab_key] = tab_results['curve_data']
    
    if 'tab3' in results['tabs']:
        validation_items = validate_scope_totals(
            find_sheet_for_tab(sheets, 'Emissions Baseline', 2),
            results['tabs']['tab3']['questions'],
            carrier_name
        )
        results['manual_review_items'].extend(validation_items)
    
    if 'tab4' in results['tabs']:
        validation_items = validate_q5_reduction_scopes(
            results['tabs']['tab4']['questions'],
            carrier_name
        )
        results['manual_review_items'].extend(validation_items)
    
    results['raw_percentage'] = round(results['total_raw'] / results['max_raw'] * 100, 1) if results['max_raw'] > 0 else 0
    results['weighted_percentage'] = round(results['total_weighted'] / results['max_weighted'] * 100, 1) if results['max_weighted'] > 0 else 0
    
    return results

# =============================================================================
# CURVE SCORING UTILITY
# =============================================================================

def calculate_curve_scores(all_results, question_key, tab_key='tab4'):
    """Calculate graded curve scores based on all carrier responses."""
    values = []
    for carrier_name, results in all_results.items():
        if tab_key in results.get('tabs', {}):
            curve_data = results['tabs'][tab_key].get('curve_data', {})
            if question_key in curve_data:
                val = curve_data[question_key]
                if val is not None and val > 0:
                    values.append((carrier_name, val))
    
    if not values:
        return {}
    
    sorted_values = sorted(values, key=lambda x: x[1], reverse=True)
    n = len(sorted_values)
    curved_scores = {}
    
    for i, (carrier_name, val) in enumerate(sorted_values):
        if n == 1:
            percentile = 1.0
        else:
            percentile = 1 - (i / (n - 1))
        
        if percentile >= 0.8:
            score = 5
        elif percentile >= 0.6:
            score = 4
        elif percentile >= 0.4:
            score = 3
        elif percentile >= 0.2:
            score = 2
        else:
            score = 1
        
        curved_scores[carrier_name] = {
            'score': score,
            'value': val,
            'percentile': round(percentile * 100, 1),
            'rank': i + 1,
            'total_carriers': n
        }
    
    return curved_scores

# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        carrier = sys.argv[2] if len(sys.argv) > 2 else "Test Carrier"
        results = score_carrier(file_path, carrier)
        
        if 'error' in results:
            print(f"Error: {results['error']}")
        else:
            print(f"\n{'='*60}")
            print(f"SCORECARD: {results['carrier_name']}")
            print(f"{'='*60}")
            print(f"Services: {results['service_type']}")
            print(f"Raw Score: {results['total_raw']}/{results['max_raw']} ({results['raw_percentage']}%)")
            print(f"Weighted Score: {results['total_weighted']}/{results['max_weighted']} ({results['weighted_percentage']}%)")
            print(f"\nManual Review Items: {len(results['manual_review_items'])}")
    else:
        print("Usage: python scoring_engine.py <excel_file> [carrier_name]")
