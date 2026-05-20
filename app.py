import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from scoring_engine import score_carrier, get_scoring_rules, TIER_WEIGHTS, calculate_curve_scores, extract_percentage

st.set_page_config(page_title="Carrier Sustainability Scorecard", page_icon="🌿", layout="wide")

if 'results' not in st.session_state:
    st.session_state.results = {}
if 'manual_reviews' not in st.session_state:
    st.session_state.manual_reviews = {}
if 'curve_scores' not in st.session_state:
    st.session_state.curve_scores = {}

def calculate_all_curve_scores():
    """Calculate curve scores for all curve-based questions across all carriers"""
    if not st.session_state.results:
        return {}
    
    curve_scores = {}
    
    # Q3 - Company reduction (tab4)
    q3_curves = calculate_curve_scores(st.session_state.results, 'Q3', 'tab4')
    if q3_curves:
        curve_scores['tab4_Q3'] = q3_curves
    
    # Q5a - Apple reduction (tab4)
    q5a_curves = calculate_curve_scores(st.session_state.results, 'Q5a', 'tab4')
    if q5a_curves:
        curve_scores['tab4_Q5a'] = q5a_curves
    
    return curve_scores

def get_curve_score_for_carrier(carrier, tab_key, q_key):
    """Get the curve-adjusted score for a specific carrier and question"""
    key = f"{tab_key}_{q_key}"
    if key in st.session_state.curve_scores:
        if carrier in st.session_state.curve_scores[key]:
            return st.session_state.curve_scores[key][carrier]
    return None

def calculate_adjusted_scores(carrier, results):
    """Calculate scores with manual review adjustments and curve scores applied"""
    adjusted_raw = results['total_raw']
    adjusted_weighted = results['total_weighted']
    
    for item in results.get('manual_review_items', []):
        key = f"{carrier}_{item['tab']}_{item['question']}"
        review = st.session_state.manual_reviews.get(key, {})
        
        # Get tier for weighted calculation
        tier = None
        original_score = item['current_score']
        for tab_key, tab_res in results.get('tabs', {}).items():
            if tab_res['name'] == item['tab']:
                q_data = tab_res['questions'].get(item['question'], {})
                tier = q_data.get('tier')
                break
        
        if review.get('status') == 'rejected':
            # Subtract the original score
            adjusted_raw -= original_score
            if tier:
                adjusted_weighted -= original_score * TIER_WEIGHTS[tier]
        elif review.get('status') == 'approved' and review.get('score') != original_score:
            # Apply manual score override
            score_diff = review.get('score', original_score) - original_score
            adjusted_raw += score_diff
            if tier:
                adjusted_weighted += score_diff * TIER_WEIGHTS[tier]
        elif review.get('status') == 'curve_applied':
            # Apply curve score
            curve_score = review.get('score', original_score)
            score_diff = curve_score - original_score
            adjusted_raw += score_diff
            if tier:
                adjusted_weighted += score_diff * TIER_WEIGHTS[tier]
    
    adjusted_raw_pct = round(adjusted_raw / results['max_raw'] * 100, 1) if results['max_raw'] > 0 else 0
    adjusted_weighted_pct = round(adjusted_weighted / results['max_weighted'] * 100, 1) if results['max_weighted'] > 0 else 0
    
    return {
        'adjusted_raw': adjusted_raw,
        'adjusted_weighted': adjusted_weighted,
        'adjusted_raw_pct': adjusted_raw_pct,
        'adjusted_weighted_pct': adjusted_weighted_pct
    }

st.title("🌿 Carrier Sustainability Scorecard")
st.write("Upload carrier survey responses to automatically score and rank sustainability performance")

with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("""
    1. Upload carrier Excel files
    2. Review automatic scores
    3. Approve/Reject manual items
    4. Apply curve scoring
    5. Export results
    """)
    st.divider()
    st.header("📊 Scoring Tiers")
    st.markdown("🔴 **Tier 1** (Critical): 3x\n\n🟡 **Tier 2** (Important): 2x\n\n🟢 **Tier 3** (Bonus): 1x\n\n⚪ **Unscored**: 0x")
    st.divider()
    st.header("📈 Curve Scoring")
    st.markdown("Questions marked with 📊 use graded curve based on all carrier responses")
    st.divider()
    if st.button("🗑️ Clear All Data"):
        st.session_state.results = {}
        st.session_state.manual_reviews = {}
        st.session_state.curve_scores = {}
        st.rerun()

st.header("📁 Upload Carrier Surveys")
uploaded_files = st.file_uploader("Drag and drop Excel files here", type=['xlsx', 'xls'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Calculate Scores", type="primary"):
        progress = st.progress(0)
        for i, file in enumerate(uploaded_files):
            carrier_name = file.name.replace('.xlsx', '').replace('.xls', '').replace('_', ' ')
            results = score_carrier(file, carrier_name)
            if 'error' not in results:
                st.session_state.results[carrier_name] = results
                for item in results.get('manual_review_items', []):
                    key = f"{carrier_name}_{item['tab']}_{item['question']}"
                    if key not in st.session_state.manual_reviews:
                        st.session_state.manual_reviews[key] = {
                            'status': 'pending',
                            'score': item['current_score'],
                            'is_curve': item.get('is_curve', False)
                        }
            else:
                st.error(f"Error processing {file.name}: {results['error']}")
            progress.progress((i + 1) / len(uploaded_files))
        
        # Calculate curve scores after all carriers are processed
        st.session_state.curve_scores = calculate_all_curve_scores()
        
        st.success("✅ All files processed! Curve scores calculated.")
        st.rerun()

if st.session_state.results:
    # Recalculate curves if needed
    if not st.session_state.curve_scores and len(st.session_state.results) > 0:
        st.session_state.curve_scores = calculate_all_curve_scores()
    
    st.header("🏆 Master Ranking")
    ranking_data = []
    for carrier, results in st.session_state.results.items():
        adjusted = calculate_adjusted_scores(carrier, results)
        pending = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') == 'pending'])
        approved = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') in ['approved', 'curve_applied']])
        rejected = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') == 'rejected'])
        
        ranking_data.append({
            'Carrier': carrier,
            'Services': results.get('service_type', 'Unknown'),
            'Original Score': results.get('total_weighted', 0),
            'Adjusted Score': adjusted['adjusted_weighted'],
            'Adjusted %': adjusted['adjusted_weighted_pct'],
            'Pending': pending,
            'Reviewed': approved + rejected
        })
    ranking_df = pd.DataFrame(ranking_data).sort_values('Adjusted %', ascending=False).reset_index(drop=True)
    ranking_df.index = ranking_df.index + 1
    ranking_df.index.name = 'Rank'
    st.dataframe(ranking_df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(ranking_df, x='Carrier', y='Adjusted %', color='Adjusted %', color_continuous_scale='Greens', title='Carrier Scores (Adjusted)')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(ranking_df, values='Adjusted Score', names='Carrier', title='Score Distribution')
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.header("📊 Detailed Analysis")
    selected = st.selectbox("Select carrier:", list(st.session_state.results.keys()))

    if selected:
        res = st.session_state.results[selected]
        adjusted = calculate_adjusted_scores(selected, res)
        
        st.subheader("📈 Score Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Original Raw", f"{res['total_raw']}/{res['max_raw']}", f"{res['raw_percentage']}%")
        c2.metric("Original Weighted", f"{res['total_weighted']}/{res['max_weighted']}", f"{res['weighted_percentage']}%")
        
        raw_delta = adjusted['adjusted_raw'] - res['total_raw']
        weighted_delta = adjusted['adjusted_weighted'] - res['total_weighted']
        c3.metric("Adjusted Raw", f"{adjusted['adjusted_raw']}/{res['max_raw']}", f"{raw_delta:+.0f} pts" if raw_delta != 0 else "No change")
        c4.metric("Adjusted Weighted", f"{adjusted['adjusted_weighted']}/{res['max_weighted']}", f"{weighted_delta:+.0f} pts" if weighted_delta != 0 else "No change")
        
        st.caption(f"Services: {res.get('service_type', 'Unknown')}")

        st.subheader("📑 Section Breakdown")
        tab_data = []
        for tab_key, tab_res in res.get('tabs', {}).items():
            pct = round(tab_res['raw_score'] / tab_res['max_raw'] * 100, 1) if tab_res['max_raw'] > 0 else 0
            status = "✅" if pct >= 80 else "⚠️" if pct >= 60 else "❌"
            tab_data.append({
                'Section': tab_res['name'],
                'Score': f"{tab_res['raw_score']}/{tab_res['max_raw']}",
                '%': f"{pct}%",
                'Status': status
            })
        st.dataframe(pd.DataFrame(tab_data), hide_index=True, use_container_width=True)

        st.subheader("📝 Question Details")
        for tab_key, tab_res in res.get('tabs', {}).items():
            with st.expander(f"📁 {tab_res['name']}"):
                for q_key, q_data in tab_res.get('questions', {}).items():
                    tier = q_data.get('tier')
                    is_unscored = q_data.get('unscored', False) or tier is None
                    is_curve = q_data.get('is_curve', False)
                    
                    if is_unscored:
                        tier_icon = "⚪"
                        tier_label = "Unscored"
                    elif tier == 1:
                        tier_icon = "🔴"
                        tier_label = "Tier 1"
                    elif tier == 2:
                        tier_icon = "🟡"
                        tier_label = "Tier 2"
                    else:
                        tier_icon = "🟢"
                        tier_label = "Tier 3"
                    
                    curve_label = " 📊 CURVE" if is_curve else ""
                    st.markdown(f"**{q_key}**: {q_data['description']} {tier_icon} {tier_label}{curve_label}")
                    
                    # Show curve info if applicable
                    if is_curve:
                        curve_info = get_curve_score_for_carrier(selected, tab_key, q_key)
                        if curve_info:
                            st.info(f"📊 Curve Score: **{curve_info['score']}/5** | Reported: {curve_info['value']}% | Rank: {curve_info['rank']}/{curve_info['total_carriers']} | Percentile: {curve_info['percentile']}%")
                    
                    st.write(f"Score: **{q_data['raw_score']}/{q_data['max_pts']}** | {q_data['justification']}")
                    if q_data.get('value'):
                        st.caption(f"Response: {q_data['value'][:150]}...")
                    st.divider()

    st.divider()
    st.header("🔍 Manual Review")
    
    # Show summary
    total_items = 0
    pending_count = 0
    approved_count = 0
    rejected_count = 0
    curve_count = 0
    
    for carrier, res in st.session_state.results.items():
        for item in res.get('manual_review_items', []):
            total_items += 1
            key = f"{carrier}_{item['tab']}_{item['question']}"
            status = st.session_state.manual_reviews.get(key, {}).get('status', 'pending')
            if status == 'pending':
                pending_count += 1
            elif status == 'approved':
                approved_count += 1
            elif status == 'rejected':
                rejected_count += 1
            elif status == 'curve_applied':
                curve_count += 1
    
    st.markdown(f"""
    **Review Progress:** {approved_count + rejected_count + curve_count}/{total_items} completed
    - 🟡 Pending: **{pending_count}**
    - 🟢 Approved: **{approved_count}**  
    - 🔴 Rejected: **{rejected_count}**
    - 📊 Curve Applied: **{curve_count}**
    """)
    
    st.divider()
    
    # Collect items
    items = []
    for carrier, res in st.session_state.results.items():
        for item in res.get('manual_review_items', []):
            key = f"{carrier}_{item['tab']}_{item['question']}"
            status = st.session_state.manual_reviews.get(key, {}).get('status', 'pending')
            tier = None
            tab_key_found = None
            for tab_key, tab_res in res.get('tabs', {}).items():
                if tab_res['name'] == item['tab']:
                    q_data = tab_res['questions'].get(item['question'], {})
                    tier = q_data.get('tier')
                    tab_key_found = tab_key
                    break
            items.append({
                'key': key,
                'carrier': carrier,
                'status': status,
                'tier': tier,
                'tab_key': tab_key_found,
                **item
            })

    if items:
        filter_opt = st.selectbox("Filter:", ['All', 'Pending', 'Approved', 'Rejected', 'Curve Applied'])
        if filter_opt == 'Curve Applied':
            filtered = [i for i in items if i['status'] == 'curve_applied']
        elif filter_opt != 'All':
            filtered = [i for i in items if i['status'].lower() == filter_opt.lower()]
        else:
            filtered = items
        
        for item in filtered:
            key = item['key']
            review = st.session_state.manual_reviews.get(key, {})
            current_status = review.get('status', 'pending')
            is_curve = item.get('is_curve', False)
            
            # Status indicator
            if current_status == 'pending':
                status_icon = "🟡"
                status_text = "PENDING"
            elif current_status == 'approved':
                status_icon = "🟢"
                status_text = "APPROVED"
            elif current_status == 'curve_applied':
                status_icon = "📊"
                status_text = "CURVE APPLIED"
            else:
                status_icon = "🔴"
                status_text = "REJECTED"
            
            original_score = item['current_score']
            tier = item.get('tier', 1)
            weighted_impact = original_score * TIER_WEIGHTS.get(tier, 1) if tier else 0
            
            curve_label = " 📊 CURVE SCORING" if is_curve else ""
            st.markdown(f"### {status_icon} {item['carrier']} | {item['tab']} - {item['question']}{curve_label}")
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{item['description']}**")
            with col2:
                st.metric("Auto Score", f"{original_score}/{item['max_score']}")
            with col3:
                current_score = review.get('score', original_score)
                current_weighted = current_score * TIER_WEIGHTS.get(tier, 1) if tier else 0
                if current_status == 'rejected':
                    st.metric("Final Score", "0", f"-{original_score}")
                else:
                    delta = current_score - original_score
                    st.metric("Final Score", f"{current_score}", f"{delta:+d}" if delta != 0 else None)
            
            # Show curve info if applicable
            if is_curve:
                curve_info = get_curve_score_for_carrier(item['carrier'], item['tab_key'], item['question'])
                if curve_info:
                    st.info(f"📊 **Curve Analysis:** Reported {curve_info['value']}% | Rank {curve_info['rank']} of {curve_info['total_carriers']} carriers | Percentile: {curve_info['percentile']}% | **Suggested Score: {curve_info['score']}/5**")
            
            item_value = item.get('value', '')
            if len(item_value) > 200:
                st.write(f"**Response:** {item_value[:200]}...")
            else:
                st.write(f"**Response:** {item_value}")
            st.caption(f"Review Criteria: {item['review_criteria']}")
            st.caption(f"Justification: {item['justification']}")
            
            # Action buttons
            if is_curve:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    curve_info = get_curve_score_for_carrier(item['carrier'], item['tab_key'], item['question'])
                    curve_score = curve_info['score'] if curve_info else original_score
                    if st.button(f"📊 Apply Curve ({curve_score})", key=f"curve_{key}", 
                               disabled=current_status == 'curve_applied',
                               use_container_width=True,
                               type="primary" if current_status == 'pending' else "secondary"):
                        st.session_state.manual_reviews[key] = {'status': 'curve_applied', 'score': curve_score, 'is_curve': True}
                        st.rerun()
                with c2:
                    if st.button("✅ Approve Auto", key=f"a_{key}", 
                               disabled=current_status == 'approved',
                               use_container_width=True):
                        st.session_state.manual_reviews[key] = {'status': 'approved', 'score': original_score, 'is_curve': True}
                        st.rerun()
                with c3:
                    if st.button("❌ Reject (0)", key=f"r_{key}", 
                               disabled=current_status == 'rejected',
                               use_container_width=True):
                        st.session_state.manual_reviews[key] = {'status': 'rejected', 'score': 0, 'is_curve': True}
                        st.rerun()
                with c4:
                    manual_score = st.number_input("Manual:", 0, item['max_score'], 
                                                   review.get('score', original_score), 
                                                   key=f"s_{key}")
                    if st.button("💾 Set", key=f"set_{key}"):
                        st.session_state.manual_reviews[key] = {'status': 'approved', 'score': manual_score, 'is_curve': True}
                        st.rerun()
            else:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("✅ Approve", key=f"a_{key}", 
                               disabled=current_status == 'approved',
                               use_container_width=True,
                               type="primary" if current_status == 'pending' else "secondary"):
                        st.session_state.manual_reviews[key] = {'status': 'approved', 'score': original_score}
                        st.rerun()
                with c2:
                    if st.button("❌ Reject", key=f"r_{key}", 
                               disabled=current_status == 'rejected',
                               use_container_width=True):
                        st.session_state.manual_reviews[key] = {'status': 'rejected', 'score': 0}
                        st.rerun()
                with c3:
                    if current_status != 'pending':
                        if st.button("↩️ Reset", key=f"reset_{key}"):
                            st.session_state.manual_reviews[key] = {'status': 'pending', 'score': original_score}
                            st.rerun()
                with c4:
                    manual_score = st.number_input("Score:", 0, item['max_score'], 
                                                   review.get('score', original_score), 
                                                   key=f"s_{key}")
                    if st.button("💾 Set", key=f"set_{key}"):
                        st.session_state.manual_reviews[key] = {'status': 'approved', 'score': manual_score}
                        st.rerun()
            
            st.divider()
    else:
        st.info("No manual review items.")

    st.divider()
    
    # Export Section
    st.header("📥 Export Results")
    
    st.subheader("📊 Final Adjusted Scores")
    final_data = []
    for carrier, results in st.session_state.results.items():
        adjusted = calculate_adjusted_scores(carrier, results)
        final_data.append({
            'Carrier': carrier,
            'Original Weighted': results.get('total_weighted', 0),
            'Adjusted Weighted': adjusted['adjusted_weighted'],
            'Change': adjusted['adjusted_weighted'] - results.get('total_weighted', 0),
            'Final %': adjusted['adjusted_weighted_pct']
        })
    final_df = pd.DataFrame(final_data).sort_values('Final %', ascending=False)
    st.dataframe(final_df, hide_index=True, use_container_width=True)
    
    if st.button("📊 Download Excel Report", type="primary"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Rankings
            export_ranking = []
            for carrier, results in st.session_state.results.items():
                adjusted = calculate_adjusted_scores(carrier, results)
                export_ranking.append({
                    'Rank': 0,
                    'Carrier': carrier,
                    'Services': results.get('service_type', 'Unknown'),
                    'Original Raw Score': results.get('total_raw', 0),
                    'Original Weighted Score': results.get('total_weighted', 0),
                    'Adjusted Raw Score': adjusted['adjusted_raw'],
                    'Adjusted Weighted Score': adjusted['adjusted_weighted'],
                    'Adjusted %': adjusted['adjusted_weighted_pct'],
                    'Max Raw': results.get('max_raw', 0),
                    'Max Weighted': results.get('max_weighted', 0)
                })
            export_df = pd.DataFrame(export_ranking).sort_values('Adjusted %', ascending=False).reset_index(drop=True)
            export_df['Rank'] = range(1, len(export_df) + 1)
            export_df.to_excel(writer, sheet_name='Rankings', index=False)
            
            # Manual review decisions
            review_data = []
            for carrier, res in st.session_state.results.items():
                for item in res.get('manual_review_items', []):
                    key = f"{carrier}_{item['tab']}_{item['question']}"
                    review = st.session_state.manual_reviews.get(key, {})
                    
                    # Get curve info
                    curve_info = None
                    if item.get('is_curve'):
                        for tab_key, tab_res in res.get('tabs', {}).items():
                            if tab_res['name'] == item['tab']:
                                curve_info = get_curve_score_for_carrier(carrier, tab_key, item['question'])
                                break
                    
                    review_data.append({
                        'Carrier': carrier,
                        'Section': item['tab'],
                        'Question': item['question'],
                        'Description': item['description'],
                        'Original Score': item['current_score'],
                        'Max Score': item['max_score'],
                        'Decision': review.get('status', 'pending').upper(),
                        'Final Score': review.get('score', item['current_score']) if review.get('status') != 'rejected' else 0,
                        'Is Curve': 'Yes' if item.get('is_curve') else 'No',
                        'Curve Rank': curve_info['rank'] if curve_info else '',
                        'Curve Percentile': curve_info['percentile'] if curve_info else '',
                        'Response': item.get('value', '')[:200]
                    })
            if review_data:
                pd.DataFrame(review_data).to_excel(writer, sheet_name='Manual Reviews', index=False)
            
            # Curve analysis
            if st.session_state.curve_scores:
                curve_data = []
                for q_key, carriers in st.session_state.curve_scores.items():
                    for carrier, info in carriers.items():
                        curve_data.append({
                            'Question': q_key,
                            'Carrier': carrier,
                            'Reported Value': info['value'],
                            'Rank': info['rank'],
                            'Total Carriers': info['total_carriers'],
                            'Percentile': info['percentile'],
                            'Curve Score': info['score']
                        })
                if curve_data:
                    pd.DataFrame(curve_data).to_excel(writer, sheet_name='Curve Analysis', index=False)
            
            # Detailed scores per carrier
            for carrier, res in st.session_state.results.items():
                data = []
                for tab_key, tab_res in res.get('tabs', {}).items():
                    for q_key, q_data in tab_res.get('questions', {}).items():
                        data.append({
                            'Section': tab_res['name'],
                            'Question': q_key,
                            'Description': q_data['description'],
                            'Tier': q_data.get('tier', 'N/A'),
                            'Score': q_data['raw_score'],
                            'Max': q_data['max_pts'],
                            'Is Curve': 'Yes' if q_data.get('is_curve') else 'No',
                            'Justification': q_data['justification'],
                            'Response': q_data.get('value', '')[:500]
                        })
                pd.DataFrame(data).to_excel(writer, sheet_name=carrier[:31], index=False)
        output.seek(0)
        st.download_button("⬇️ Download Excel Report", output, f"Scorecard_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", 
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("👆 Upload carrier Excel files to get started!")
