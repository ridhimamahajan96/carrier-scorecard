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
        return 5, f"Numeric response provided: {value}"
    return 0, "No numeric value found"

def score_completion_text(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 5, f"Response provided: {str(value)[:100]}..."

def score_url_provided(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 2, f"Documentation provided: {str(value)[:100]}..."

def score_tab3_q4(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    recognized = ['ghg protocol', 'sbti', 'glec', 'iso 14083', 'ecotransit']
    if any(fw in value_lower for fw in recognized):
        return 5, f"Recognized framework selected: {value}"
    elif 'internal' in value_lower and 'not sure' not in value_lower and 'none' not in value_lower:
        return 2, "Only Internal Framework selected"
    elif 'not sure' in value_lower or 'none' in value_lower:
        return 1, "Not sure/None selected"
    return 0, "No valid framework identified"

def score_tab3_q6(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    valid_options = ['ttw', 'wtw', 'wtt']
    has_valid = any(opt in value_lower for opt in valid_options)
    has_wtw = 'wtw' in value_lower or 'well to wheel' in value_lower
    only_not_sure = 'not sure' in value_lower and not has_valid
    if only_not_sure:
        return 1, "Only Not sure selected"
    elif has_valid:
        base_score = 5
        bonus = 2 if has_wtw else 0
        total = base_score + bonus
        justification = f"Valid boundary selected: {value}"
        if has_wtw:
            justification += " (includes WTW +2 bonus)"
        return total, justification
    return 0, "No valid boundary selected"

def score_tab3_q7(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 5, f"Response provided: {value}"

def score_tab3_q8(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    scope_count = 0
    scopes_found = []
    if 'scope 1' in value_lower or 'scope1' in value_lower:
        scope_count += 1
        scopes_found.append('Scope 1')
    if 'scope 2' in value_lower or 'scope2' in value_lower:
        scope_count += 1
        scopes_found.append('Scope 2')
    if 'scope 3' in value_lower or 'scope3' in value_lower:
        scope_count += 1
        scopes_found.append('Scope 3')
    if scope_count == 3:
        return 5, f"All 3 scopes selected"
    elif scope_count == 2:
        return 4, f"2 scopes selected"
    elif scope_count == 1:
        return 3, f"1 scope selected"
    return 0, "No scopes identified"

def score_tab4_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    if 'yes' in value_lower and 'no' not in value_lower:
        return 5, "Yes - has carbon neutrality goal"
    elif 'development' in value_lower or 'in progress' in value_lower:
        return 2, "In development"
    elif 'no' in value_lower:
        return 1, "No carbon neutrality goal"
    return 0, f"Unrecognized response: {value}"

def score_tab4_q2(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_str = str(value)
    if '2030' in value_str and '2031' not in value_str:
        return 5, "Target year: 2030"
    elif any(str(y) in value_str for y in range(2031, 2041)):
        return 4, f"Target year: 2031-2040"
    elif any(str(y) in value_str for y in range(2041, 2050)):
        return 3, f"Target year: 2041-2050"
    elif '2050' in value_str and 'beyond' not in value_str.lower():
        return 2, "Target year: 2050"
    elif 'beyond' in value_str.lower():
        return 1, f"Target year: Beyond 2050"
    return 0, f"Could not determine target year"

def score_tab4_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    if 'not sure' in value_lower:
        return 0, "Not sure selected"
    return 5, f"Reduction target provided: {value}"

def score_tab4_q4(value, q3_value=None, **kwargs):
    if q3_value is None:
        return 0, "Q3 value not available"
    q3_lower = str(q3_value).lower() if q3_value else ''
    if 'not sure' not in q3_lower:
        return 0, "N/A - Q3 was not Not sure"
    if is_blank(value):
        return 0, "Q3 was Not sure but no estimate provided"
    if has_numeric(value):
        return 3, f"Estimate provided: {value}"
    return 0, "No numeric estimate found"

def score_tab4_q5a(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_str = str(value).lower()
    numbers = re.findall(r'(\d+)', value_str)
    if numbers:
        max_num = max(int(n) for n in numbers)
        if max_num == 0:
            return 0, "0% reduction"
        elif max_num <= 10:
            return 1, f"{max_num}% reduction (1-10% range)"
        elif max_num <= 20:
            return 2, f"{max_num}% reduction (11-20% range)"
        elif max_num <= 40:
            return 3, f"{max_num}% reduction (21-40% range)"
        elif max_num <= 50:
            return 4, f"{max_num}% reduction (41-50% range)"
        else:
            return 5, f"{max_num}% reduction (51%+ range)"
    return 0, f"Could not determine reduction"

def score_tab4_q6(value, fy2030_value=None, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_str = str(value)
    years_mentioned = sum(1 for year in ['2026', '2027', '2028', '2029', '2030'] if year in value_str)
    if years_mentioned >= 4:
        return 5, "Comprehensive ramp plan provided"
    elif years_mentioned >= 1:
        return 2, f"Partial ramp plan ({years_mentioned} years mentioned)"
    return 0, "No clear ramp plan identified"

def score_tab5_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    if 'yes' in value_lower:
        return 5, "Yes - carbon credits part of strategy"
    elif 'development' in value_lower:
        return 3, "In development"
    elif 'no' in value_lower:
        return 2, "No - carbon credits not part of strategy"
    return 0, f"Unrecognized response: {value}"

def score_tab5_q2(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    recognized = ['nature-based', 'nature based', 'voluntary', 'regulatory', 'compliance']
    has_recognized = any(r in value_lower for r in recognized)
    only_others = 'other' in value_lower and not has_recognized
    if has_recognized:
        return 5, f"Recognized instruments selected: {value}"
    elif only_others:
        return 2, "Only Others selected"
    return 0, "No valid instruments identified"

def score_conditional_text(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent question value not available"
    depends_lower = str(depends_value).lower() if depends_value else ''
    if condition and condition.lower() not in depends_lower:
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, f"{condition} was selected but no explanation provided"
    return 3, f"Explanation provided (needs manual review)"

def score_conditional_text_2pts(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent question value not available"
    depends_lower = str(depends_value).lower() if depends_value else ''
    if condition and condition.lower() not in depends_lower:
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, f"{condition} was selected but no explanation provided"
    return 2, f"Explanation provided (needs manual review)"

def score_tab6_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    has_saf = 'saf' in value_lower or 'sustainable aviation fuel' in value_lower
    recognized_others = ['fleet modernisation', 'fleet modernization', 'route optimisation', 'route optimization', 'payload', 'load factor']
    has_other_recognized = any(r in value_lower for r in recognized_others)
    only_others = 'other' in value_lower and not has_saf and not has_other_recognized
    if has_saf:
        return 5, f"SAF selected: {value}"
    elif has_other_recognized:
        return 3, f"Recognized strategy (non-SAF): {value}"
    elif only_others:
        return 1, "Only Others selected"
    return 0, "No valid strategy identified"

def score_tab7_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    recognized = ['alternative fuel', 'vessel efficiency', 'route optimisation', 'route optimization', 'slow steaming']
    has_recognized = any(r in value_lower for r in recognized)
    only_others = 'other' in value_lower and not has_recognized
    if has_recognized:
        return 5, f"Recognized strategy selected: {value}"
    elif only_others:
        return 1, "Only Others selected"
    return 0, "No valid strategy identified"

def score_tab7_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    recognized = ['lng', 'bio-lng', 'e-lng', 'methanol', 'bio-methanol', 'e-methanol', 'ammonia']
    has_recognized = any(r in value_lower for r in recognized)
    only_others = 'other' in value_lower and not has_recognized
    if has_recognized:
        return 5, f"Recognized fuel selected: {value}"
    elif only_others:
        return 1, "Only Others selected"
    return 0, "No valid fuel identified"

def score_tab8_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    recognized = ['electric', 'bev', 'hybrid', 'alternative fuel', 'biofuel', 'route optimisation', 'route optimization', 'load consolidation']
    has_recognized = any(r in value_lower for r in recognized)
    only_others = 'other' in value_lower and not has_recognized
    if has_recognized:
        return 5, f"Recognized strategy selected: {value}"
    elif only_others:
        return 1, "Only Others selected"
    return 0, "No valid strategy identified"

def score_tab8_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    value_lower = str(value).lower()
    recognized = ['biofuel', 'renewable diesel', 'rng', 'hvo', 'biodiesel', 'bio-cng', 'bio-lng', 'hydrogen', 'fuel cell']
    has_recognized = any(r in value_lower for r in recognized)
    only_others = 'other' in value_lower and not has_recognized
    if has_recognized:
        return 5, f"Recognized fuel selected: {value}"
    elif only_others:
        return 1, "Only Others selected"
    return 0, "No valid fuel identified"

def get_scoring_rules():
    rules = {
        'tab3': {
            'name': 'Emissions Baseline',
            'section': 2,
            'questions': {
                'Q4': {'description': 'GHG reporting frameworks used', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q4},
                'Q6': {'description': 'Emissions reporting boundary', 'tier': 2, 'max_pts': 7, 'manual_review': False, 'score_func': score_tab3_q6},
                'Q7': {'description': 'Unit for reporting emissions', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q7},
                'Q8': {'description': 'Scopes included in reporting', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q8},
                'Q9': {'description': 'Company total GHG emissions FY 2025', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q10': {'description': 'Company Scope 1 breakdown', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q11': {'description': 'Company Scope 2 breakdown', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q12': {'description': 'Company Scope 3 breakdown', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q13': {'description': 'Apple-specific total emissions FY 2025', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q14': {'description': 'Apple Scope 1', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q15': {'description': 'Apple Scope 2', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q16': {'description': 'Apple Scope 3', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_numeric},
                'Q17': {'description': 'Methodology for Apple allocation', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
                'Q18': {'description': 'Documentation for methodology', 'tier': 3, 'max_pts': 2, 'manual_review': False, 'score_func': score_url_provided},
                'Q19': {'description': 'Third-party verification details', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
                'Q20': {'description': 'Documentation for verification', 'tier': 3, 'max_pts': 2, 'manual_review': False, 'score_func': score_url_provided},
            }
        },
        'tab4': {
            'name': 'Reduction Targets',
            'section': 3,
            'questions': {
                'Q1': {'description': 'Carbon neutrality goal', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q1},
                'Q2': {'description': 'Target year for carbon neutrality', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q2},
                'Q3': {'description': 'Company emissions reduction by FY 2030', 'tier': 3, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q3},
                'Q4': {'description': 'If Not sure - provide estimate', 'tier': 3, 'max_pts': 3, 'manual_review': False, 'score_func': score_tab4_q4, 'depends_on': 'Q3'},
                'Q5a': {'description': 'Apple overall emissions reduction FY 2030', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q5a},
                'Q6': {'description': 'YoY ramp plan FY 2026-2030', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q6},
            }
        },
        'tab5': {
            'name': 'Carbon Credits',
            'section': 4,
            'questions': {
                'Q1': {'description': 'Carbon credits part of strategy', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab5_q1},
                'Q2': {'description': 'Carbon credit instruments used', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab5_q2},
                'Q3': {'description': 'Explain Others (Carbon Credits)', 'tier': 3, 'max_pts': 3, 'manual_review': True, 'review_criteria': 'Verify carbon credit strategy', 'score_func': score_conditional_text, 'depends_on': 'Q2', 'condition': 'Others'},
                'Q4': {'description': 'Quality of carbon credits', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
                'Q5': {'description': 'Near-term approach residual emissions', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
            }
        },
        'tab6': {
            'name': 'Air Freight',
            'section': 5,
            'conditional': 'Air',
            'questions': {
                'Q1': {'description': 'Air decarbonisation strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab6_q1},
                'Q2': {'description': 'Explain Others (Air)', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify strategy', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
                'Q3': {'description': 'Company SAF strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review SAF strategy quality', 'score_func': score_completion_text},
                'Q4': {'description': 'Apple-specific SAF strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review Apple SAF commitments', 'score_func': score_completion_text},
            }
        },
        'tab7': {
            'name': 'Ocean Freight',
            'section': 6,
            'conditional': 'Ocean',
            'questions': {
                'Q1': {'description': 'Ocean decarbonisation strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab7_q1},
                'Q2': {'description': 'Explain Others (Ocean)', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify strategy', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
                'Q3': {'description': 'Alternative fuels for ocean', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab7_q3},
                'Q4': {'description': 'Explain Others (Ocean fuels)', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify fuel detail', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q3', 'condition': 'Others'},
                'Q5': {'description': 'Company alternative fuel strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review fuel strategy', 'score_func': score_completion_text},
                'Q6': {'description': 'Apple-specific ocean strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review Apple commitments', 'score_func': score_completion_text},
            }
        },
        'tab8': {
            'name': 'Ground Freight',
            'section': 7,
            'conditional': 'Ground',
            'questions': {
                'Q1': {'description': 'Ground decarbonisation strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab8_q1},
                'Q2': {'description': 'Explain Others (Ground)', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify strategy', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
                'Q3': {'description': 'Alternative fuels for ground', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab8_q3},
                'Q4': {'description': 'Explain Others (Ground fuels)', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify fuel detail', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q3', 'condition': 'Others'},
                'Q5': {'description': 'Company EV/alt fuel strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review EV strategy', 'score_func': score_completion_text},
                'Q6': {'description': 'Apple-specific ground strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review Apple commitments', 'score_func': score_completion_text},
            }
        }
    }
    return rules

def detect_services(sheets):
    services = set()
    for sheet_name, df in sheets.items():
        df_str = df.to_string().lower()
        if 'air' in df_str:
            services.add('Air')
        if 'ocean' in df_str or 'sea' in df_str or 'maritime' in df_str:
            services.add('Ocean')
        if 'ground' in df_str or 'road' in df_str or 'truck' in df_str:
            services.add('Ground')
    if not services:
        services = {'Air', 'Ocean', 'Ground'}
    return services

def find_sheet_for_tab(sheets, tab_name, section_num):
    for sheet_name, df in sheets.items():
        sheet_lower = sheet_name.lower()
        if tab_name.lower().split()[0] in sheet_lower:
            return df
        if f'section {section_num}' in sheet_lower:
            return df
    sheet_list = list(sheets.values())
    tab_index = section_num
    if tab_index < len(sheet_list):
        return sheet_list[tab_index]
    return None

def extract_question_value(df, question_key):
    if df is None:
        return None
    q_num = question_key.replace('Q', '').replace('a', '').replace('b', '').replace('c', '').replace('d', '')
    for idx, row in df.iterrows():
        row_str = ' '.join(str(v) for v in row.values if pd.notna(v))
        if f'Q{q_num}' in row_str or f'q{q_num}' in row_str.lower():
            for col_idx, val in enumerate(row.values):
                if col_idx > 0 and pd.notna(val) and str(val).strip():
                    if len(str(val)) > 5:
                        return val
            if idx + 1 < len(df):
                next_row = df.iloc[idx + 1]
                for val in next_row.values:
                    if pd.notna(val) and str(val).strip():
                        return val
    return None

def score_tab(sheets, tab_key, tab_rules, all_rules):
    tab_results = {
        'name': tab_rules['name'],
        'section': tab_rules['section'],
        'questions': {},
        'raw_score': 0,
        'weighted_score': 0,
        'max_raw': 0,
        'max_weighted': 0,
        'manual_review_items': []
    }
    sheet_data = find_sheet_for_tab(sheets, tab_rules['name'], tab_rules['section'])
    if sheet_data is None:
        return tab_results
    for q_key, q_rules in tab_rules['questions'].items():
        value = extract_question_value(sheet_data, q_key)
        depends_value = None
        if 'depends_on' in q_rules:
            depends_value = extract_question_value(sheet_data, q_rules['depends_on'])
        score_func = q_rules['score_func']
        condition = q_rules.get('condition')
        if 'depends_on' in q_rules:
            score, justification = score_func(value, depends_value=depends_value, condition=condition)
        else:
            score, justification = score_func(value)
        tier = q_rules['tier']
        weighted_score = score * TIER_WEIGHTS[tier]
        max_weighted = q_rules['max_pts'] * TIER_WEIGHTS[tier]
        tab_results['questions'][q_key] = {
            'description': q_rules['description'],
            'tier': tier,
            'raw_score': score,
            'max_pts': q_rules['max_pts'],
            'weighted_score': weighted_score,
            'max_weighted': max_weighted,
            'justification': justification,
            'value': str(value)[:200] if value else '',
            'manual_review': q_rules.get('manual_review', False)
        }
        tab_results['raw_score'] += score
        tab_results['weighted_score'] += weighted_score
        tab_results['max_raw'] += q_rules['max_pts']
        tab_results['max_weighted'] += max_weighted
        if q_rules.get('manual_review', False) and score > 0:
            tab_results['manual_review_items'].append({
                'tab': tab_rules['name'],
                'question': q_key,
                'description': q_rules['description'],
                'value': str(value)[:500] if value else '',
                'current_score': score,
                'max_score': q_rules['max_pts'],
                'review_criteria': q_rules.get('review_criteria', 'Review response quality'),
                'justification': justification
            })
    return tab_results

def score_carrier(excel_file, carrier_name=None):
    try:
        xlsx = pd.ExcelFile(excel_file)
        sheets = {sheet: pd.read_excel(xlsx, sheet_name=sheet) for sheet in xlsx.sheet_names}
    except Exception as e:
        return {'error': f"Could not read Excel file: {str(e)}"}
    services = detect_services(sheets)
    rules = get_scoring_rules()
    results = {
        'carrier_name': carrier_name or 'Unknown',
        'services': services,
        'service_type': '+'.join(sorted(services)) if services else 'Unknown',
        'tabs': {},
        'manual_review_items': [],
        'total_raw': 0,
        'total_weighted': 0,
        'max_raw': 0,
        'max_weighted': 0
    }
    for tab_key, tab_rules in rules.items():
        if 'conditional' in tab_rules:
            if tab_rules['conditional'] not in services:
                continue
        tab_results = score_tab(sheets, tab_key, tab_rules, rules)
        results['tabs'][tab_key] = tab_results
        results['total_raw'] += tab_results['raw_score']
        results['total_weighted'] += tab_results['weighted_score']
        results['max_raw'] += tab_results['max_raw']
        results['max_weighted'] += tab_results['max_weighted']
        results['manual_review_items'].extend(tab_results['manual_review_items'])
    if results['max_raw'] > 0:
        results['raw_percentage'] = round(results['total_raw'] / results['max_raw'] * 100, 1)
    else:
        results['raw_percentage'] = 0
    if results['max_weighted'] > 0:
        results['weighted_percentage'] = round(results['total_weighted'] / results['max_weighted'] * 100, 1)
    else:
        results['weighted_percentage'] = 0
    return results
