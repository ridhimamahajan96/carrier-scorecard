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

def get_adjusted_score(carrier, results):
    adjusted_raw = results['total_raw']
    adjusted_weighted = results['total_weighted']
    
    for item in results.get('manual_review_items', []):
        key = f"{carrier}|{item['tab']}|{item['question']}"
        review = st.session_state.manual_reviews.get(key, {})
        
        if review.get('status') == 'rejected':
            tier = 2
            for tab_data in results.get('tabs', {}).values():
                for q_key, q_data in tab_data.get('questions', {}).items():
                    if q_key == item['question'] and tab_data['name'] == item['tab']:
                        tier = q_data['tier']
            adjusted_raw -= item['current_score']
            adjusted_weighted -= item['current_score'] * TIER_WEIGHTS[tier]
        elif review.get('status') == 'edited':
            old_score = item['current_score']
            new_score = review.get('score', old_score)
            tier = 2
            for tab_data in results.get('tabs', {}).values():
                for q_key, q_data in tab_data.get('questions', {}).items():
                    if q_key == item['question'] and tab_data['name'] == item['tab']:
                        tier = q_data['tier']
            adjusted_raw += (new_score - old_score)
            adjusted_weighted += (new_score - old_score) * TIER_WEIGHTS[tier]
    
    return {
        'raw': adjusted_raw,
        'weighted': adjusted_weighted,
        'raw_pct': round(adjusted_raw / results['max_raw'] * 100, 1) if results['max_raw'] > 0 else 0,
        'weighted_pct': round(adjusted_weighted / results['max_weighted'] * 100, 1) if results['max_weighted'] > 0 else 0
    }

st.title("🌿 Carrier Sustainability Scorecard")

with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("1. Upload carrier Excel files\n2. Click Calculate Scores\n3. Approve/Reject manual items\n4. Export results")
    st.divider()
    st.header("📊 Scoring Tiers")
    st.markdown("🔴 **Tier 1**: 3x\n🟡 **Tier 2**: 2x\n🟢 **Tier 3**: 1x")
    st.divider()
    if st.button("🗑️ Clear All"):
        st.session_state.results = {}
        st.session_state.manual_reviews = {}
        st.rerun()

st.header("📁 Upload Carrier Surveys")
uploaded_files = st.file_uploader("Drag and drop Excel files", type=['xlsx', 'xls'], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Calculate Scores", type="primary"):
    for file in uploaded_files:
        carrier_name = file.name.replace('.xlsx', '').replace('.xls', '').replace('_', ' ')
        results = score_carrier(file, carrier_name)
        if 'error' not in results:
            st.session_state.results[carrier_name] = results
            for item in results.get('manual_review_items', []):
                key = f"{carrier_name}|{item['tab']}|{item['question']}"
                if key not in st.session_state.manual_reviews:
                    st.session_state.manual_reviews[key] = {'status': 'pending', 'score': item['current_score']}
    st.rerun()

if st.session_state.results:
    
    # Calculate totals
    total_pending = 0
    for carrier, results in st.session_state.results.items():
        for item in results.get('manual_review_items', []):
            key = f"{carrier}|{item['tab']}|{item['question']}"
            if st.session_state.manual_reviews.get(key, {}).get('status') == 'pending':
                total_pending += 1
    
    # Rankings
    st.header("🏆 Master Ranking")
    
    if total_pending > 0:
        st.warning(f"⚠️ {total_pending} items pending manual review - scores may change")
    else:
        st.success("✅ All reviews complete - scores are final")
    
    ranking_data = []
    for carrier, results in st.session_state.results.items():
        adj = get_adjusted_score(carrier, results)
        ranking_data.append({
            'Carrier': carrier,
            'Services': results.get('service_type', 'Unknown'),
            'Auto Score': results['total_raw'],
            'Final Score': adj['raw'],
            'Max': results['max_raw'],
            'Final %': adj['raw_pct']
        })
    
    ranking_df = pd.DataFrame(ranking_data).sort_values('Final %', ascending=False).reset_index(drop=True)
    ranking_df.insert(0, 'Rank', range(1, len(ranking_df) + 1))
    st.dataframe(ranking_df, hide_index=True, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(ranking_df, x='Carrier', y='Final %', color='Final %', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(ranking_df, values='Final Score', names='Carrier')
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Manual Review Section
    st.header("🔍 Manual Review")
    
    items = []
    for carrier, res in st.session_state.results.items():
        for item in res.get('manual_review_items', []):
            key = f"{carrier}|{item['tab']}|{item['question']}"
            review = st.session_state.manual_reviews.get(key, {'status': 'pending', 'score': item['current_score']})
            items.append({
                'key': key,
                'carrier': carrier,
                'status': review['status'],
                'review_score': review['score'],
                **item
            })
    
    if items:
        # Filter
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox("Filter:", ['All', 'Pending', 'Approved', 'Rejected'])
        with col2:
            st.metric("Pending Reviews", total_pending)
        
        filtered = items if filter_status == 'All' else [i for i in items if i['status'] == filter_status.lower()]
        
        # Display each item
        for item in filtered:
            key = item['key']
            review = st.session_state.manual_reviews.get(key, {})
            status = review.get('status', 'pending')
            
            # Get tier
            tier = 2
            for tab_data in st.session_state.results[item['carrier']].get('tabs', {}).values():
                for q_key, q_data in tab_data.get('questions', {}).items():
                    if q_key == item['question'] and tab_data['name'] == item['tab']:
                        tier = q_data['tier']
            
            tier_icon = "🔴" if tier == 1 else "🟡" if tier == 2 else "🟢"
            weight = TIER_WEIGHTS[tier]
            auto_pts = item['current_score']
            auto_weighted = auto_pts * weight
            
            # Calculate current final score based on status
            if status == 'approved':
                final_pts = auto_pts
                status_display = "✅ APPROVED"
                box_color = "#d4edda"
                border_color = "#28a745"
            elif status == 'rejected':
                final_pts = 0
                status_display = "❌ REJECTED"
                box_color = "#f8d7da"
                border_color = "#dc3545"
            else:
                final_pts = auto_pts
                status_display = "🟡 PENDING"
                box_color = "#fff3cd"
                border_color = "#ffc107"
            
            final_weighted = final_pts * weight
            change = final_weighted - auto_weighted
            
            # Display box
            st.markdown(f"""
            <div style="background-color: {box_color}; border-left: 5px solid {border_color}; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <div style="display: flex; justify-content: space-between;">
                    <strong>{item['carrier']} | {item['tab']} - {item['question']}</strong>
                    <span><strong>{status_display}</strong></span>
                </div>
                <div style="margin-top: 10px;">
                    <strong>{item['description']}</strong> {tier_icon} Tier {tier} (×{weight})
                </div>
                <div style="color: #666; margin-top: 5px;">
                    Response: {item['value'][:200]}{'...' if len(item['value']) > 200 else ''}
                </div>
                <div style="margin-top: 10px; font-size: 16px;">
                    <strong>Auto: {auto_pts}/{item['max_score']} pts ({auto_weighted} weighted)</strong>
                    &nbsp;→&nbsp;
                    <strong style="color: {border_color};">Final: {final_pts}/{item['max_score']} pts ({final_weighted} weighted)</strong>
                    &nbsp;
                    <span style="color: {'green' if change > 0 else 'red' if change < 0 else 'gray'};">
                        ({'+' if change >= 0 else ''}{change} change)
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"✅ Approve", key=f"approve_{key}", disabled=(status == 'approved')):
                    st.session_state.manual_reviews[key] = {'status': 'approved', 'score': auto_pts}
                    st.rerun()
            
            with col2:
                if st.button(f"❌ Reject (0 pts)", key=f"reject_{key}", disabled=(status == 'rejected')):
                    st.session_state.manual_reviews[key] = {'status': 'rejected', 'score': 0}
                    st.rerun()
            
            with col3:
                if status != 'pending':
                    if st.button(f"↩️ Reset", key=f"reset_{key}"):
                        st.session_state.manual_reviews[key] = {'status': 'pending', 'score': auto_pts}
                        st.rerun()
            
            st.markdown("---")
        
        # Approve All / Reject All buttons
        st.subheader("Bulk Actions")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Approve All Pending", type="primary"):
                for item in items:
                    if st.session_state.manual_reviews.get(item['key'], {}).get('status') == 'pending':
                        st.session_state.manual_reviews[item['key']] = {'status': 'approved', 'score': item['current_score']}
                st.rerun()
        with col2:
            if st.button("❌ Reject All Pending"):
                for item in items:
                    if st.session_state.manual_reviews.get(item['key'], {}).get('status') == 'pending':
                        st.session_state.manual_reviews[item['key']] = {'status': 'rejected', 'score': 0}
                st.rerun()
        with col3:
            if st.button("↩️ Reset All"):
                for item in items:
                    st.session_state.manual_reviews[item['key']] = {'status': 'pending', 'score': item['current_score']}
                st.rerun()
    
    else:
        st.success("✅ No manual review items - all scores are automatic!")
    
    st.divider()
    
    # Detailed Analysis
    st.header("📊 Detailed Analysis")
    selected = st.selectbox("Select carrier:", list(st.session_state.results.keys()))
    
    if selected:
        res = st.session_state.results[selected]
        adj = get_adjusted_score(selected, res)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Auto Score", f"{res['total_raw']}/{res['max_raw']}")
        col2.metric("Final Score", f"{adj['raw']}/{res['max_raw']}", f"{adj['raw'] - res['total_raw']:+d}")
        col3.metric("Final %", f"{adj['raw_pct']}%")
        
        for tab_key, tab_res in res.get('tabs', {}).items():
            with st.expander(f"📁 {tab_res['name']} ({tab_res['raw_score']}/{tab_res['max_raw']})"):
                for q_key, q_data in tab_res.get('questions', {}).items():
                    tier_icon = "🔴" if q_data['tier'] == 1 else "🟡" if q_data['tier'] == 2 else "🟢"
                    
                    review_key = f"{selected}|{tab_res['name']}|{q_key}"
                    review = st.session_state.manual_reviews.get(review_key, {})
                    
                    if review.get('status') == 'rejected':
                        st.markdown(f"**{q_key}** {tier_icon} | ~~{q_data['raw_score']}~~ → **0/{q_data['max_pts']}** ❌")
                    elif review.get('status') == 'approved':
                        st.markdown(f"**{q_key}** {tier_icon} | **{q_data['raw_score']}/{q_data['max_pts']}** ✅")
                    else:
                        st.markdown(f"**{q_key}** {tier_icon} | **{q_data['raw_score']}/{q_data['max_pts']}**")
                    
                    st.caption(f"{q_data['description']} — {q_data['justification']}")
    
    st.divider()
    
    # Export
    st.header("📥 Export")
    
    if st.button("📊 Download Excel Report", type="primary"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Rankings
            export_data = []
            for carrier, results in st.session_state.results.items():
                adj = get_adjusted_score(carrier, results)
                export_data.append({
                    'Rank': 0,
                    'Carrier': carrier,
                    'Services': results.get('service_type'),
                    'Auto Score': results['total_raw'],
                    'Final Score': adj['raw'],
                    'Max': results['max_raw'],
                    'Final %': adj['raw_pct']
                })
            export_df = pd.DataFrame(export_data).sort_values('Final %', ascending=False)
            export_df['Rank'] = range(1, len(export_df) + 1)
            export_df.to_excel(writer, sheet_name='Rankings', index=False)
            
            # Details per carrier
            for carrier, results in st.session_state.results.items():
                rows = []
                for tab_key, tab_res in results.get('tabs', {}).items():
                    for q_key, q_data in tab_res.get('questions', {}).items():
                        review_key = f"{carrier}|{tab_res['name']}|{q_key}"
                        review = st.session_state.manual_reviews.get(review_key, {})
                        
                        if review.get('status') == 'rejected':
                            final = 0
                            status = 'Rejected'
                        elif review.get('status') == 'approved':
                            final = q_data['raw_score']
                            status = 'Approved'
                        else:
                            final = q_data['raw_score']
                            status = 'Auto'
                        
                        rows.append({
                            'Section': tab_res['name'],
                            'Question': q_key,
                            'Description': q_data['description'],
                            'Tier': q_data['tier'],
                            'Auto': q_data['raw_score'],
                            'Final': final,
                            'Max': q_data['max_pts'],
                            'Status': status,
                            'Response': q_data['value'][:300]
                        })
                pd.DataFrame(rows).to_excel(writer, sheet_name=carrier[:31], index=False)
        
        output.seek(0)
        st.download_button("⬇️ Download", output, f"Scorecard_{datetime.now().strftime('%Y%m%d')}.xlsx")

else:
    st.info("👆 Upload carrier Excel files to get started!")
