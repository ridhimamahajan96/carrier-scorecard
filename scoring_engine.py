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
    v = str(value).lower().strip()
    if v in ['not applicable', 'n/a', 'na', 'nil', '-']:
        return 0, "Not Applicable - no emissions attributed"
    if v in ['0', '0%', '0.0', '0.00', '0.0%']:
        return 0, "Zero emissions reported - 0 pts"
    nums = re.findall(r'[\d.]+', v)
    if nums:
        num_val = float(nums[0])
        if num_val == 0:
            return 0, "Zero emissions reported - 0 pts"
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
    return 0, f"No valid framework: {value}"

def score_tab3_q6(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    has_valid = any(opt in v for opt in ['ttw', 'wtw', 'wtt', 'tank to wheel', 'well to wheel', 'well to tank'])
    has_wtw = 'wtw' in v or 'well to wheel' in v
    if 'not sure' in v and not has_valid:
        return 1, "Only Not sure selected"
    elif has_valid:
        score = 5 + (2 if has_wtw else 0)
        return score, f"Valid boundary: {value}" + (" (+2 WTW bonus)" if has_wtw else "")
    return 0, f"No valid boundary: {value}"

def score_tab3_q7(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    return 5, f"Response: {value}"

def score_tab3_q8(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
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

def score_tab4_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower().strip()
    if v == 'yes':
        return 5, "Yes - has carbon neutrality goal"
    elif 'development' in v or 'in progress' in v:
        return 2, "In development"
    elif v == 'no':
        return 1, "No carbon neutrality goal"
    return 0, f"Unrecognized: {value}"

def score_tab4_q2(value, **kwargs):
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
        if n == 0:
            return 0, "0% reduction"
        elif n <= 10:
            return 1, f"{n}% (1-10%)"
        elif n <= 20:
            return 2, f"{n}% (11-20%)"
        elif n <= 40:
            return 3, f"{n}% (21-40%)"
        elif n <= 50:
            return 4, f"{n}% (41-50%)"
        else:
            return 5, f"{n}% (51%+)"
    return 0, f"Could not determine: {value}"

def score_tab4_q6(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value)
    years = sum(1 for y in ['2026', '2027', '2028', '2029', '2030'] if y in v)
    if years >= 4:
        return 5, f"Comprehensive ramp plan: {value}"
    elif years >= 1:
        return 2, f"Partial plan ({years} years)"
    nums = re.findall(r'(\d+)', v)
    if nums:
        return 5, f"Ramp plan provided: {value}"
    return 0, "No ramp plan identified"

def score_tab5_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower().strip()
    if v == 'yes':
        return 5, "Yes - carbon credits in strategy"
    elif 'development' in v:
        return 3, "In development"
    elif v == 'no':
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
    return 0, f"No valid instruments: {value}"

def score_conditional_text(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent value not available"
    if condition and condition.lower() not in str(depends_value).lower():
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, "No explanation provided"
    return 3, f"Explanation provided: {str(value)[:50]}"

def score_conditional_text_2pts(value, depends_value=None, condition=None, **kwargs):
    if depends_value is None:
        return 0, "Dependent value not available"
    if condition and condition.lower() not in str(depends_value).lower():
        return 0, f"N/A - {condition} not selected"
    if is_blank(value):
        return 0, "No explanation provided"
    return 2, f"Explanation provided: {str(value)[:50]}"

def score_tab6_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if 'saf' in v or 'sustainable aviation fuel' in v:
        return 5, f"SAF selected: {value}"
    elif any(r in v for r in ['fleet', 'route', 'payload', 'load factor', 'modernisation', 'modernization', 'optimisation', 'optimization']):
        return 3, f"Recognized strategy: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid strategy: {value}"

def score_tab7_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['alternative fuel', 'vessel efficiency', 'route', 'slow steaming', 'optimisation', 'optimization']):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid strategy: {value}"

def score_tab7_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['lng', 'methanol', 'ammonia', 'bio-lng', 'e-lng', 'bio-methanol', 'e-methanol']):
        return 5, f"Recognized fuel: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid fuel: {value}"

def score_tab8_q1(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['electric', 'bev', 'hybrid', 'alternative fuel', 'biofuel', 'route', 'load', 'ev']):
        return 5, f"Recognized: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid strategy: {value}"

def score_tab8_q3(value, **kwargs):
    if is_blank(value):
        return 0, "Blank response"
    v = str(value).lower()
    if any(r in v for r in ['biofuel', 'renewable diesel', 'rng', 'hvo', 'biodiesel', 'hydrogen', 'fuel cell', 'bio-cng', 'bio-lng']):
        return 5, f"Recognized fuel: {value}"
    elif 'other' in v:
        return 1, "Only Others"
    return 0, f"No valid fuel: {value}"

def get_scoring_rules():
    return {
        'tab3': {'name': 'Emissions Baseline', 'section': 2, 'questions': {
            'Q4': {'description': 'GHG reporting frameworks', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q4, 'is_checkbox': True},
            'Q6': {'description': 'Emissions reporting boundary', 'tier': 2, 'max_pts': 7, 'manual_review': False, 'score_func': score_tab3_q6, 'is_checkbox': True},
            'Q7': {'description': 'Unit for reporting', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q7, 'is_checkbox': True},
            'Q8': {'description': 'Scopes included', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab3_q8, 'is_checkbox': True},
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
            'Q5a': {'description': 'Apple reduction FY2030', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q5a, 'is_sub_row': True, 'sub_row_text': 'overall'},
            'Q6': {'description': 'YoY ramp plan', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab4_q6, 'is_checkbox': True}}},
        'tab5': {'name': 'Carbon Credits', 'section': 4, 'questions': {
            'Q1': {'description': 'Carbon credits in strategy', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab5_q1},
            'Q2': {'description': 'Credit instruments', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab5_q2, 'is_checkbox': True},
            'Q3': {'description': 'Explain Others', 'tier': 3, 'max_pts': 3, 'manual_review': True, 'review_criteria': 'Verify strategy', 'score_func': score_conditional_text, 'depends_on': 'Q2', 'condition': 'Others'},
            'Q4': {'description': 'Quality of credits', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text},
            'Q5': {'description': 'Near-term approach', 'tier': 2, 'max_pts': 5, 'manual_review': False, 'score_func': score_completion_text}}},
        'tab6': {'name': 'Air Freight', 'section': 5, 'conditional': 'Air', 'questions': {
            'Q1': {'description': 'Air strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab6_q1, 'is_checkbox': True},
            'Q2': {'description': 'Explain Others', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
            'Q3': {'description': 'SAF strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review SAF', 'score_func': score_completion_text},
            'Q4': {'description': 'Apple SAF strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review Apple SAF', 'score_func': score_completion_text}}},
        'tab7': {'name': 'Ocean Freight', 'section': 6, 'conditional': 'Ocean', 'questions': {
            'Q1': {'description': 'Ocean strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab7_q1, 'is_checkbox': True},
            'Q2': {'description': 'Explain Others', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
            'Q3': {'description': 'Alternative fuels', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab7_q3, 'is_checkbox': True},
            'Q4': {'description': 'Explain Others fuels', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q3', 'condition': 'Others'},
            'Q5': {'description': 'Company fuel strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text},
            'Q6': {'description': 'Apple ocean strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text}}},
        'tab8': {'name': 'Ground Freight', 'section': 7, 'conditional': 'Ground', 'questions': {
            'Q1': {'description': 'Ground strategies', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab8_q1, 'is_checkbox': True},
            'Q2': {'description': 'Explain Others', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q1', 'condition': 'Others'},
            'Q3': {'description': 'Alternative fuels', 'tier': 1, 'max_pts': 5, 'manual_review': False, 'score_func': score_tab8_q3, 'is_checkbox': True},
            'Q4': {'description': 'Explain Others fuels', 'tier': 3, 'max_pts': 2, 'manual_review': True, 'review_criteria': 'Verify', 'score_func': score_conditional_text_2pts, 'depends_on': 'Q3', 'condition': 'Others'},
            'Q5': {'description': 'Company EV strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text},
            'Q6': {'description': 'Apple ground strategy', 'tier': 2, 'max_pts': 5, 'manual_review': True, 'review_criteria': 'Review', 'score_func': score_completion_text}}}
    }

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

def extract_checkbox_values(df, start_idx):
    selected = []
    idx = start_idx + 1
    while idx < len(df):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        if col_a.upper().startswith('Q') and col_a[1:].replace('a','').replace('b','').isdigit():
            break
        if len(row) > 2:
            col_b = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            col_c = row.iloc[2] if pd.notna(row.iloc[2]) else ''
            col_c_str = str(col_c).strip().lower()
            is_checked = col_c_str in ['true', '1', 'x', '✓', '☑', 'yes'] or col_c_str == 'true' or (isinstance(col_c, bool) and col_c)
            if is_checked and col_b and 'check box' not in col_b.lower() and 'select' not in col_b.lower():
                selected.append(col_b)
            if col_c_str and col_c_str not in ['false', '0', '', 'nan', 'na', 'n/a'] and 'check box' not in col_c_str and 'select' not in col_c_str:
                if not is_checked and col_b:
                    selected.append(col_b)
        idx += 1
    return ', '.join(selected) if selected else None

def extract_sub_row_value(df, start_idx, sub_text):
    idx = start_idx + 1
    while idx < len(df):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        if col_a.upper().startswith('Q') and len(col_a) > 1:
            break
        if len(row) > 2:
            col_b = str(row.iloc[1]).strip().lower() if pd.notna(row.iloc[1]) else ''
            if sub_text.lower() in col_b:
                col_c = row.iloc[2] if pd.notna(row.iloc[2]) else None
                if col_c and str(col_c).strip():
                    return str(col_c).strip()
        idx += 1
    return None

def extract_ramp_plan_values(df, start_idx):
    values = {}
    idx = start_idx + 1
    while idx < len(df):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        if col_a.upper().startswith('Q') and col_a[1:].isdigit():
            break
        if len(row) > 2:
            col_b = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            col_c = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
            for year in ['2026', '2027', '2028', '2029', '2030']:
                if year in col_b and col_c:
                    values[year] = col_c
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
    
    for idx, row in df.iterrows():
        col_a = str(row.iloc[0]).strip().upper() if len(row) > 0 and pd.notna(row.iloc[0]) else ''
        
        if col_a == f'Q{q_num}':
            if is_checkbox:
                return extract_checkbox_values(df, idx)
            elif is_sub_row and sub_row_text:
                return extract_sub_row_value(df, idx, sub_row_text)
            elif question_key == 'Q6' and q_rules and q_rules.get('description', '').lower().find('ramp') >= 0:
                return extract_ramp_plan_values(df, idx)
            else:
                if len(row) > 2:
                    col_c = row.iloc[2]
                    if pd.notna(col_c) and str(col_c).strip():
                        val = str(col_c).strip()
                        if 'check box' not in val.lower() and 'select' not in val.lower():
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
            score, justification = q_rules['score_func'](value, depends_value=depends_value, condition=condition)
        else:
            score, justification = q_rules['score_func'](value)
        
        tier = q_rules['tier']
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
            'manual_review': q_rules.get('manual_review', False)
        }
        
        tab_results['raw_score'] += score
        tab_results['weighted_score'] += weighted
        tab_results['max_raw'] += q_rules['max_pts']
        tab_results['max_weighted'] += max_weighted
        
        if q_rules.get('manual_review') and score > 0:
            tab_results['manual_review_items'].append({
                'tab': tab_rules['name'],
                'question': q_key,
                'description': q_rules['description'],
                'value': str(value)[:500] if value else '',
                'current_score': score,
                'max_score': q_rules['max_pts'],
                'review_criteria': q_rules.get('review_criteria', 'Review'),
                'justification': justification
            })
    
    return tab_results

def score_carrier(excel_file, carrier_name=None):
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
        'max_weighted': 0
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
    
    results['raw_percentage'] = round(results['total_raw'] / results['max_raw'] * 100, 1) if results['max_raw'] > 0 else 0
    results['weighted_percentage'] = round(results['total_weighted'] / results['max_weighted'] * 100, 1) if results['max_weighted'] > 0 else 0
    
    return results
