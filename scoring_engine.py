import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from scoring_engine import score_carrier, get_scoring_rules, TIER_WEIGHTS

st.set_page_config(page_title="Carrier Sustainability Scorecard", page_icon="🌿", layout="wide")

if 'results' not in st.session_state:
    st.session_state.results = {}
if 'manual_reviews' not in st.session_state:
    st.session_state.manual_reviews = {}
if 'review_complete' not in st.session_state:
    st.session_state.review_complete = {}

def calculate_adjusted_scores(carrier, results):
    """Calculate scores with manual review adjustments"""
    adjusted_raw = results['total_raw']
    adjusted_weighted = results['total_weighted']
    
    for item in results.get('manual_review_items', []):
        key = f"{carrier}_{item['tab']}_{item['question']}"
        review = st.session_state.manual_reviews.get(key, {})
        
        if review.get('status') == 'rejected':
            tier = 2
            for tab_key, tab_data in results.get('tabs', {}).items():
                for q_key, q_data in tab_data.get('questions', {}).items():
                    if q_key == item['question'] and tab_data['name'] == item['tab']:
                        tier = q_data['tier']
                        break
            
            adjusted_raw -= item['current_score']
            adjusted_weighted -= item['current_score'] * TIER_WEIGHTS[tier]
        
        elif review.get('status') == 'edited':
            old_score = item['current_score']
            new_score = review.get('score', old_score)
            tier = 2
            for tab_key, tab_data in results.get('tabs', {}).items():
                for q_key, q_data in tab_data.get('questions', {}).items():
                    if q_key == item['question'] and tab_data['name'] == item['tab']:
                        tier = q_data['tier']
                        break
            
            score_diff = new_score - old_score
            adjusted_raw += score_diff
            adjusted_weighted += score_diff * TIER_WEIGHTS[tier]
    
    adjusted_raw_pct = round(adjusted_raw / results['max_raw'] * 100, 1) if results['max_raw'] > 0 else 0
    adjusted_weighted_pct = round(adjusted_weighted / results['max_weighted'] * 100, 1) if results['max_weighted'] > 0 else 0
    
    return {
        'raw': adjusted_raw,
        'weighted': adjusted_weighted,
        'raw_pct': adjusted_raw_pct,
        'weighted_pct': adjusted_weighted_pct
    }

st.title("🌿 Carrier Sustainability Scorecard")
st.write("Upload carrier survey responses to automatically score and rank sustainability performance")

with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("1. Upload carrier Excel files\n2. Review automatic scores\n3. Approve/Reject/Edit manual items\n4. Export results")
    st.divider()
    st.header("📊 Scoring Tiers")
    st.markdown("🔴 **Tier 1** (Critical): 3x\n\n🟡 **Tier 2** (Important): 2x\n\n🟢 **Tier 3** (Bonus): 1x")
    st.divider()
    
    total_pending = 0
    for carrier, results in st.session_state.results.items():
        for item in results.get('manual_review_items', []):
            key = f"{carrier}_{item['tab']}_{item['question']}"
            if st.session_state.manual_reviews.get(key, {}).get('status', 'pending') == 'pending':
                total_pending += 1
    
    if total_pending > 0:
        st.warning(f"⚠️ {total_pending} items need review")
    elif st.session_state.results:
        st.success("✅ All reviews complete!")
    
    st.divider()
    if st.button("🗑️ Clear All Data"):
        st.session_state.results = {}
        st.session_state.manual_reviews = {}
        st.session_state.review_complete = {}
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
                        st.session_state.manual_reviews[key] = {'status': 'pending', 'score': item['current_score']}
            else:
                st.error(f"Error: {results['error']}")
            progress.progress((i + 1) / len(uploaded_files))
        st.success("✅ All files processed!")
        st.rerun()

if st.session_state.results:
    st.header("🏆 Master Ranking")
    
    ranking_data = []
    for carrier, results in st.session_state.results.items():
        adjusted = calculate_adjusted_scores(carrier, results)
        pending = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') == 'pending'])
        
        ranking_data.append({
            'Carrier': carrier,
            'Services': results.get('service_type', 'Unknown'),
            'Auto Score': results.get('total_raw', 0),
            'Adjusted Score': adjusted['raw'],
            'Max': results.get('max_raw', 0),
            'Auto %': results.get('raw_percentage', 0),
            'Final %': adjusted['raw_pct'],
            'Pending': pending,
            'Status': '✅ Complete' if pending == 0 else f'⚠️ {pending} pending'
        })
    
    ranking_df = pd.DataFrame(ranking_data).sort_values('Final %', ascending=False).reset_index(drop=True)
    ranking_df.index = ranking_df.index + 1
    ranking_df.index.name = 'Rank'
    
    st.dataframe(
        ranking_df[['Carrier', 'Services', 'Auto Score', 'Adjusted Score', 'Max', 'Final %', 'Status']],
        use_container_width=True
    )
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(ranking_df, x='Carrier', y='Final %', color='Final %', color_continuous_scale='Greens', title='Final Carrier Scores')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(ranking_df, values='Adjusted Score', names='Carrier', title='Score Distribution')
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Manual Review Section - IMPROVED
    st.header("🔍 Manual Review")
    st.write("Review flagged items and approve, reject, or edit scores. **Changes are saved automatically.**")
    
    items = []
    for carrier, res in st.session_state.results.items():
        for item in res.get('manual_review_items', []):
            key = f"{carrier}_{item['tab']}_{item['question']}"
            status = st.session_state.manual_reviews.get(key, {}).get('status', 'pending')
            current_score = st.session_state.manual_reviews.get(key, {}).get('score', item['current_score'])
            items.append({'key': key, 'carrier': carrier, 'status': status, 'current_score': current_score, **item})
    
    if items:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            filter_opt = st.selectbox("Filter by status:", ['All', 'Pending', 'Approved', 'Rejected', 'Edited'])
        with col2:
            filter_carrier = st.selectbox("Filter by carrier:", ['All'] + list(st.session_state.results.keys()))
        with col3:
            st.metric("Pending", len([i for i in items if i['status'] == 'pending']))
        
        filtered = items
        if filter_opt != 'All':
            filtered = [i for i in filtered if i['status'].lower() == filter_opt.lower()]
        if filter_carrier != 'All':
            filtered = [i for i in filtered if i['carrier'] == filter_carrier]
        
        for item in filtered:
            key = item['key']
            review = st.session_state.manual_reviews.get(key, {'status': 'pending', 'score': item['current_score']})
            
            # Status colors
            if review['status'] == 'pending':
                border_color = "#ffc107"
                bg_color = "#fff9e6"
                status_icon = "🟡"
                status_text = "PENDING REVIEW"
            elif review['status'] == 'approved':
                border_color = "#28a745"
                bg_color = "#e8f5e9"
                status_icon = "✅"
                status_text = "APPROVED"
            elif review['status'] == 'rejected':
                border_color = "#dc3545"
                bg_color = "#ffebee"
                status_icon = "❌"
                status_text = "REJECTED (0 pts)"
            else:  # edited
                border_color = "#17a2b8"
                bg_color = "#e3f2fd"
                status_icon = "✏️"
                status_text = f"EDITED ({review['score']} pts)"
            
            # Get tier for this question
            tier = 2
            for tab_key, tab_data in st.session_state.results[item['carrier']].get('tabs', {}).items():
                for q_key, q_data in tab_data.get('questions', {}).items():
                    if q_key == item['question'] and tab_data['name'] == item['tab']:
                        tier = q_data['tier']
                        break
            
            tier_icon = "🔴" if tier == 1 else "🟡" if tier == 2 else "🟢"
            weight = TIER_WEIGHTS[tier]
            
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; background-color: {bg_color}; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 16px;">{item['carrier']} | {item['tab']} - {item['question']}</span>
                    <span style="font-weight: bold; color: {border_color};">{status_icon} {status_text}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{item['description']}** {tier_icon} Tier {tier} ({weight}x weight)")
                st.write(f"**Response:** {item['value'][:300]}..." if len(item['value']) > 300 else f"**Response:** {item['value']}")
                st.caption(f"📋 Review Criteria: {item['review_criteria']}")
            
            with col2:
                st.markdown("**Score Impact:**")
                
                auto_score = item['current_score']
                auto_weighted = auto_score * weight
                
                if review['status'] == 'approved':
                    final_score = auto_score
                elif review['status'] == 'rejected':
                    final_score = 0
                elif review['status'] == 'edited':
                    final_score = review['score']
                else:
                    final_score = auto_score
                
                final_weighted = final_score * weight
                
                if review['status'] != 'pending':
                    change = final_weighted - auto_weighted
                    change_text = f"+{change}" if change > 0 else str(change)
                    change_color = "green" if change > 0 else "red" if change < 0 else "gray"
                    
                    st.markdown(f"""
                    Auto: **{auto_score}/{item['max_score']}** ({auto_weighted} weighted)  
                    Final: **{final_score}/{item['max_score']}** ({final_weighted} weighted)  
                    <span style="color: {change_color};">Change: {change_text} weighted pts</span>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    Auto: **{auto_score}/{item['max_score']}** ({auto_weighted} weighted)  
                    *Make a decision below*
                    """, unsafe_allow_html=True)
            
            # Action buttons
            st.markdown("**Actions:**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                approve_disabled = review['status'] == 'approved'
                if st.button("✅ Approve", key=f"a_{key}", disabled=approve_disabled, use_container_width=True):
                    st.session_state.manual_reviews[key] = {'status': 'approved', 'score': item['current_score']}
                    st.rerun()
            
            with col2:
                reject_disabled = review['status'] == 'rejected'
                if st.button("❌ Reject (0 pts)", key=f"r_{key}", disabled=reject_disabled, use_container_width=True):
                    st.session_state.manual_reviews[key] = {'status': 'rejected', 'score': 0}
                    st.rerun()
            
            with col3:
                new_score = st.number_input(
                    "Custom score:",
                    min_value=0,
                    max_value=item['max_score'],
                    value=review.get('score', item['current_score']),
                    key=f"s_{key}"
                )
            
            with col4:
                if st.button("💾 Save Custom", key=f"sv_{key}", use_container_width=True):
                    st.session_state.manual_reviews[key] = {'status': 'edited', 'score': new_score}
                    st.rerun()
            
            # Reset button
            if review['status'] != 'pending':
                if st.button("↩️ Reset to Pending", key=f"reset_{key}"):
                    st.session_state.manual_reviews[key] = {'status': 'pending', 'score': item['current_score']}
                    st.rerun()
            
            st.divider()
    else:
        st.success("✅ No manual review items found - all scores are automatic!")
    
    st.divider()
    
    # Detailed Analysis
    st.header("📊 Detailed Carrier Analysis")
    selected = st.selectbox("Select carrier:", list(st.session_state.results.keys()))
    
    if selected:
        res = st.session_state.results[selected]
        adjusted = calculate_adjusted_scores(selected, res)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Auto Raw Score", f"{res['total_raw']}/{res['max_raw']}", f"{res['raw_percentage']}%")
        with col2:
            diff = adjusted['raw'] - res['total_raw']
            st.metric("Final Raw Score", f"{adjusted['raw']}/{res['max_raw']}", f"{'+' if diff >= 0 else ''}{diff} pts")
        with col3:
            st.metric("Final %", f"{adjusted['raw_pct']}%")
        with col4:
            pending = len([r for r in res.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{selected}_{r['tab']}_{r['question']}", {}).get('status') == 'pending'])
            st.metric("Pending Reviews", pending)
        
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
                    tier_icon = "🔴" if q_data['tier'] == 1 else "🟡" if q_data['tier'] == 2 else "🟢"
                    
                    # Check if this question has manual review adjustment
                    review_key = f"{selected}_{tab_res['name']}_{q_key}"
                    review = st.session_state.manual_reviews.get(review_key, {})
                    
                    score_display = q_data['raw_score']
                    if review.get('status') == 'rejected':
                        score_display = 0
                        st.markdown(f"**{q_key}**: {q_data['description']} {tier_icon} — ~~{q_data['raw_score']}~~ → **0/{q_data['max_pts']}** ❌ Rejected")
                    elif review.get('status') == 'edited':
                        score_display = review['score']
                        st.markdown(f"**{q_key}**: {q_data['description']} {tier_icon} — ~~{q_data['raw_score']}~~ → **{score_display}/{q_data['max_pts']}** ✏️ Edited")
                    else:
                        st.markdown(f"**{q_key}**: {q_data['description']} {tier_icon} — **{q_data['raw_score']}/{q_data['max_pts']}**")
                    
                    st.write(f"💡 {q_data['justification']}")
                    if q_data['value']:
                        st.caption(f"Response: {q_data['value'][:150]}...")
                    st.divider()
    
    st.divider()
    
    # Export
    st.header("📥 Export Results")
    st.write("Export includes all manual review adjustments.")
    
    if st.button("📊 Download Excel Report", type="primary"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Rankings with adjusted scores
            export_ranking = []
            for carrier, results in st.session_state.results.items():
                adjusted = calculate_adjusted_scores(carrier, results)
                export_ranking.append({
                    'Rank': 0,
                    'Carrier': carrier,
                    'Services': results.get('service_type', 'Unknown'),
                    'Auto Raw Score': results.get('total_raw', 0),
                    'Final Raw Score': adjusted['raw'],
                    'Max Raw': results.get('max_raw', 0),
                    'Auto %': results.get('raw_percentage', 0),
                    'Final %': adjusted['raw_pct']
                })
            export_df = pd.DataFrame(export_ranking).sort_values('Final %', ascending=False).reset_index(drop=True)
            export_df['Rank'] = range(1, len(export_df) + 1)
            export_df.to_excel(writer, sheet_name='Rankings', index=False)
            
            # Detailed sheets per carrier
            for carrier, results in st.session_state.results.items():
                data = []
                for tab_key, tab_res in results.get('tabs', {}).items():
                    for q_key, q_data in tab_res.get('questions', {}).items():
                        review_key = f"{carrier}_{tab_res['name']}_{q_key}"
                        review = st.session_state.manual_reviews.get(review_key, {})
                        
                        auto_score = q_data['raw_score']
                        if review.get('status') == 'rejected':
                            final_score = 0
                            review_status = 'Rejected'
                        elif review.get('status') == 'edited':
                            final_score = review['score']
                            review_status = 'Edited'
                        elif review.get('status') == 'approved':
                            final_score = auto_score
                            review_status = 'Approved'
                        else:
                            final_score = auto_score
                            review_status = 'Auto' if not q_data.get('manual_review') else 'Pending'
                        
                        data.append({
                            'Section': tab_res['name'],
                            'Question': q_key,
                            'Description': q_data['description'],
                            'Tier': q_data['tier'],
                            'Auto Score': auto_score,
                            'Final Score': final_score,
                            'Max': q_data['max_pts'],
                            'Review Status': review_status,
                            'Justification': q_data['justification'],
                            'Response': q_data['value'][:500]
                        })
                pd.DataFrame(data).to_excel(writer, sheet_name=carrier[:31], index=False)
            
            # Manual reviews summary
            review_data = []
            for key, review in st.session_state.manual_reviews.items():
                parts = key.split('_')
                if len(parts) >= 3:
                    review_data.append({
                        'Carrier': parts[0],
                        'Tab': parts[1],
                        'Question': parts[2],
                        'Status': review.get('status', 'pending'),
                        'Final Score': review.get('score', 0)
                    })
            if review_data:
                pd.DataFrame(review_data).to_excel(writer, sheet_name='Manual Reviews', index=False)
        
        output.seek(0)
        st.download_button(
            "⬇️ Download Excel Report",
            output,
            f"Carrier_Scorecard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👆 Upload carrier Excel files to get started!")
