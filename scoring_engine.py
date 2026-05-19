import pandas as pd
import re

TIER_WEIGHTS = {1: 3, 2: 2, 3: 1}

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

def score_completion_numeric(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    if has_numeric(value):
        return 5, f"Numeric response: {value}"
    return 0, "No numeric value found"

def score_completion_text(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 5, f"Response: {str(value)[:100]}"

def score_url_provided(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 2, f"Documentation: {str(value)[:100]}"

def score_tab3_q4(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(fw in v for fw in ['ghg protocol', 'sbti', 'glec', 'iso 14083', 'ecotransit']):
        return 5, f"Recognized framework: {value}"
    elif 'internal' in v and 'not sure' not in v and 'none' not in v:
        return 2, "Only Internal Framework"
    elif 'not sure' in v or 'none' in v:
        return 1, "Not sure/None selected"
    return 0, "No valid framework"

def score_tab3_q6(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    has_valid = any(opt in v for opt in ['ttw', 'wtw', 'wtt'])
    has_wtw = 'wtw' in v
    if 'not sure' in v and not has_valid:
        return 1, "Only Not sure selected"
    elif has_valid:
        score = 5 + (2 if has_wtw else 0)
        return score, f"Valid boundary: {value}" + (" (+2 WTW bonus)" if has_wtw else "")
    return 0, "No valid boundary"

def score_tab3_q7(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 5, f"Response: {value}"

def score_tab3_q8(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    count = sum([1 for s in ['scope 1', 'scope 2', 'scope 3', 'scope1', 'scope2', 'scope3'] if s in v]) // 1
    count = min(count, 3)
    if 'scope 1' in v or 'scope1' in v:
        count = 1
    if 'scope 2' in v or 'scope2' in v:
        count = max(count, 1) + (1 if count >= 1 else 0)
    if 'scope 3' in v or 'scope3' in v:
        count = max(count, 1) + (1 if count >= 1 else 0)
    count = len([s for s in ['scope 1', 'scope 2', 'scope 3'] if s in v or s.replace(' ', '') in v])
    if count == 3:
        return 5, "All 3 scopes"
    elif count == 2:
        return 4, "2 scopes"
    elif count == 1:
        return 3, "1 scope"
    return 0, "No scopes identified"

def score_tab4_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if v == 'yes' or (v.startswith('yes') and 'no' not in v):
        return 5, "Yes - has carbon neutrality goal"
    elif 'development' in v or 'in progress' in v:
        return 2, "In development"
    elif v == 'no' or v.startswith('no'):
        return 1, "No carbon neutrality goal"
    return 0, f"Unrecognized: {value}"

def score_tab4_q2(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value)
    if '2030' in v and '2031' not in v:
        return 5, "Target: 2030"
    elif any(str(y) in v for y in range(2031, 2041)) or '2031-2040' in v:
        return 4, "Target: 2031-2040"
    elif any(str(y) in v for y in range(2041, 2050)) or '2041-2050' in v:
        return 3, "Target: 2041-2050"
    elif '2050' in v and 'beyond' not in v.lower():
        return 2, "Target: 2050"
    elif 'beyond' in v.lower():
        return 1, "Target: Beyond 2050"
    return 0, "Could not determine target year"

def score_tab4_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    if 'not sure' in str(value).lower():
        return 0, "Not sure selected"
    return 5, f"Reduction target: {value}"

def score_tab4_q4(value, q3_value=None, **kwargs):
    if q3_value is None or 'not sure' not in str(q3_value).lower():
        return 0, "N/A - Q3 was not Not sure"
    if is_blank(value):
        return 0, "No estimate provided"
    if has_numeric(value):
        return 3, f"Estimate: {value}"
    return 0, "No numeric estimate"

def score_tab4_q5a(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    nums = re.findall(r'(\d+)', v)
    if nums:
        n = max(int(x) for x in nums)
        if n == 0: return 0, "0% reduction"
        elif n <= 10: return 1, f"{n}% (1-10%)"
        elif n <= 20: return 2, f"{n}% (11-20%)"
        elif n <= 40: return 3, f"{n}% (21-40%)"
        elif n <= 50: return 4, f"{n}% (41-50%)"
        else: return 5, f"{n}% (51%+)"
    return 0, "Could not determine %"

def score_tab4_q6(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value)
    years = sum(1 for y in ['2026', '2027', '2028', '2029', '2030'] if y in v)
    if years >= 4:
        return 5, "Comprehensive ramp plan"
    elif years >= 1:
        return 2, f"Partial plan ({years} years)"
    return 0, "No ramp plan identified"

def score_tab5_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if v == 'yes' or v.startswith('yes'):
        return 5, "Yes - carbon credits in strategy"
    elif 'development' in v:
        return 3, "In development"
    elif v == 'no' or v.startswith('no'):
        return 2, "No carbon credits"
    return 0, f"Unrecognized: {value}"

def score_tab5_q2(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    recognized = ['nature-based', 'nature based', 'voluntary', 'regulatory', 'compliance']
    if any(r in v for r in recognized):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 2, "Only Others"
    return 0, "No valid instruments"

def score_conditional_text(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent value not available"
    if condition and condition.lower() not in str(depends_value).lower():
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, "No explanation provided"
    return 3, "Explanation provided (needs review)"

def score_conditional_text_2pts(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent value not available"
    if condition and condition.lower() not in str(depends_value).lower():
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, "No explanation provided"
    return 2, "Explanation provided (needs review)"

def score_tab6_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'saf' in v or 'sustainable aviation fuel' in v:
        return 5, f"SAF selected: {value}"
    elif any(r in v for r in ['fleet', 'route', 'payload', 'load factor']):
        return 3, f"Recognized strategy: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, "No valid strategy"

def score_tab7_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['alternative fuel', 'vessel efficiency', 'route', 'slow steaming']):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, "No valid strategy"

def score_tab7_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['lng', 'methanol', 'ammonia']):
        return 5, f"Recognized fuel: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, "No valid fuel"

def score_tab8_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['electric', 'bev', 'hybrid', 'alternative fuel', 'biofuel', 'route', 'load']):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, "No valid strategy"

def score_tab8_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['biofuel', 'renewable diesel', 'rng', 'hvo', 'biodiesel', 'hydrogen', 'fuel cell']):
        return 5, f"Recognized fuel: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, "No valid fuel"

def get_scoring_rules():
    return {
        'tab3': {'name': 'Emissions Baseline', 'section': 2, 'questions': {
            'Q4': {'description': 'GHG reporting frameworks', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q4},
            'Q6': {'description': 'Emissions reporting boundary', 'tier': 2, 'max_pts': 7, 'manual_review': False, 'score_func': score_tab3_q6},
            'Q7': {'description': 'Unit for reporting', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q7},
            'Q8': {'description': 'Scopes included', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q8},
            'Q9': {'description': 'Company total GHG FY2025', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q10': {'description': 'Company Scope 1', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q11': {'description': 'Company Scope 2', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q12': {'description': 'Company Scope 3', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q13': {'description': 'Apple total emissions', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q14': {'description': 'Apple Scope 1', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q15': {'description': 'Apple Scope 2', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q16': {'description': 'Apple Scope 3', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
            'Q17': {'description': 'Methodology for allocation', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
            'Q18': {'description': 'Documentation for methodology', 'tier': 3, 'max_pts': 2, 'manual_review': False, 'score_func': score_url_provided},
            'Q19': {'description': 'Third-party verification', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
            'Q20': {'description': 'Documentation for verification', 'tier': 3, 'max_pts': 2, 'manual_review': False, 'score_func': score_url_provided}}},
        'tab4': {'name': 'Reduction Targets', 'section': 3, 'questions': {
            'Q1': {'description': 'Carbon neutrality goal', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q1},
            'Q2': {'description': 'Target year', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q2},
            'Q3': {'description': 'Company reduction by FY2030', 'tier': 3, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q3},
            'Q4': {'description': 'If Not sure - estimate', 'tier': 3, 'max_pts': 3, 'manual_review': False, 'score_func': score_tab4_q4, 'depends_on': 'Q3'},
            'Q5a': {'description': 'Apple reduction FY2030', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q5a},
            'Q6': {'description': 'YoY ramp plan', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q6}}},
        'tab5': {'name': 'Carbon Credits', 'section': 4, 'questions': {
            'Q1': {'description': 'Carbon credits in strategy', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab5_q1},
            'Q2': {'description': 'Credit instruments', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab5_q2},
            'Q3': {'description': 'Explain Others', 'tier': 3, 'max_pts': 3, 'manual_review': True, 'review_criteria': 'Verify strategy', 'score_func': score_conditional_text, 'depends_on': 'Q2', 'condition': 'Others'},
            'Q4': {'description': 'Quality of credits', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
            'Q5': {'description': 'Near-term approach', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text}}},
        'tab6': {'name': 'Air Freight', 'section': 5, 'conditional': 'Air', 'questions': {
            'Q1': {'description': 'Air strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab6_q1},
            'Q2': {'description': 'Explain Others', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
            'Q3': {'description': 'SAF strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review SAF', 'score_func': score_completion_text},
            'Q4': {'description': 'Apple SAF strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review Apple SAF', 'score_func': score_completion_text}}},
        'tab7': {'name': 'Ocean Freight', 'section': 6, 'conditional': 'Ocean', 'questions': {
            'Q1': {'description': 'Ocean strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab7_q1},
            'Q2': {'description': 'Explain Others', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
            'Q3': {'description': 'Alternative fuels', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab7_q3},
            'Q4': {'description': 'Explain Others fuels', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q3', 'condition': 'Others'},
            'Q5': {'description': 'Company fuel strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text},
            'Q6': {'description': 'Apple ocean strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text}}},
        'tab8': {'name': 'Ground Freight', 'section': 7, 'conditional': 'Ground', 'questions': {
            'Q1': {'description': 'Ground strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab8_q1},
            'Q2': {'description': 'Explain Others', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
            'Q3': {'description': 'Alternative fuels', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab8_q3},
            'Q4': {'description': 'Explain Others fuels', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q3', 'condition': 'Others'},
            'Q5': {'description': 'Company EV strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text},
            'Q6': {'description': 'Apple ground strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text}}}
    }

def detect_services(sheets):
    services = set()
    for name, df in sheets.items():
        s = df.to_string().lower()
        if 'air' in s: services.add('Air')
        if 'ocean' in s or 'sea' in s: services.add('Ocean')
        if 'ground' in s or 'road' in s or 'truck' in s: services.add('Ground')
    return services if services else {'Air', 'Ocean', 'Ground'}

def find_sheet_for_tab(sheets, tab_name, section_num):
    for name, df in sheets.items():
        if tab_name.lower().split()[0] in name.lower():
            return df
        if f'section {section_num}' in name.lower():
            return df
    sheet_list = list(sheets.values())
    return sheet_list[section_num] if section_num < len(sheet_list) else None

def extract_question_value(df, question_key):
    if df is None:
        return None
    q_num = question_key.replace('Q', '').replace('a', '')
    
    for idx, row in df.iterrows():
        first_col = str(row.iloc[0]).strip() if len(row) > 0 else ''
        if first_col.upper() == f'Q{q_num}' or first_col == q_num:
            if len(row) > 2:
                val = row.iloc[2]
                if pd.notna(val) and str(val).strip():
                    return str(val).strip()
    return None

def score_tab(sheets, tab_key, tab_rules, all_rules):
    tab_results = {'name': tab_rules['name'], 'section': tab_rules['section'], 'questions': {}, 'raw_score': 0, 'weighted_score': 0, 'max_raw': 0, 'max_weighted': 0, 'manual_review_items': []}
    sheet = find_sheet_for_tab(sheets, tab_rules['name'], tab_rules['section'])
    if sheet is None:
        return tab_results
    for q_key, q_rules in tab_rules['questions'].items():
        value = extract_question_value(sheet, q_key)
        depends_value = extract_question_value(sheet, q_rules['depends_on']) if 'depends_on' in q_rules else None
        condition = q_rules.get('condition')
        score, justification = q_rules['score_func'](value, depends_value=depends_value, condition=condition) if 'depends_on' in q_rules else q_rules['score_func'](value)
        tier = q_rules['tier']
        weighted = score * TIER_WEIGHTS[tier]
        max_weighted = q_rules['max_pts'] * TIER_WEIGHTS[tier]
        tab_results['questions'][q_key] = {'description': q_rules['description'], 'tier': tier, 'raw_score': score, 'max_pts': q_rules['max_pts'], 'weighted_score': weighted, 'max_weighted': max_weighted, 'justification': justification, 'value': str(value)[:200] if value else '', 'manual_review': q_rules.get('manual_review', False)}
        tab_results['raw_score'] += score
        tab_results['weighted_score'] += weighted
        tab_results['max_raw'] += q_rules['max_pts']
        tab_results['max_weighted'] += max_weighted
        if q_rules.get('manual_review') and score > 0:
            tab_results['manual_review_items'].append({'tab': tab_rules['name'], 'question': q_key, 'description': q_rules['description'], 'value': str(value)[:500] if value else '', 'current_score': score, 'max_score': q_rules['max_pts'], 'review_criteria': q_rules.get('review_criteria', 'Review'), 'justification': justification})
    return tab_results

def score_carrier(excel_file, carrier_name=None):
    try:
        xlsx = pd.ExcelFile(excel_file)
        sheets = {s: pd.read_excel(xlsx, sheet_name=s) for s in xlsx.sheet_names}
    except Exception as e:
        return {'error': str(e)}
    services = detect_services(sheets)
    rules = get_scoring_rules()
    results = {'carrier_name': carrier_name or 'Unknown', 'services': services, 'service_type': '+'.join(sorted(services)), 'tabs': {}, 'manual_review_items': [], 'total_raw': 0, 'total_weighted': 0, 'max_raw': 0, 'max_weighted': 0}
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
    results['raw_percentage'] = round(results['total_raw'] / results['max_raw'] * 100, 1) if results['max_raw'] > 0 else 0
    results['weighted_percentage'] = round(results['total_weighted'] / results['max_weighted'] * 100, 1) if results['max_weighted'] > 0 else 0
    return results
