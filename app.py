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
if 'pending_changes' not in st.session_state:
    st.session_state.pending_changes = {}

def calculate_adjusted_scores(carrier, results):
    """Calculate scores with manual review adjustments applied"""
    adjusted_raw = results['total_raw']
    adjusted_weighted = results['total_weighted']
    
    for item in results.get('manual_review_items', []):
        key = f"{carrier}_{item['tab']}_{item['question']}"
        review = st.session_state.manual_reviews.get(key, {})
        
        if review.get('status') == 'rejected':
            # Subtract the original score
            adjusted_raw -= item['current_score']
            # Get tier for weighted calculation
            tier = None
            for tab_key, tab_res in results.get('tabs', {}).items():
                if tab_res['name'] == item['tab']:
                    q_data = tab_res['questions'].get(item['question'], {})
                    tier = q_data.get('tier')
                    break
            if tier:
                adjusted_weighted -= item['current_score'] * TIER_WEIGHTS[tier]
    
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
    st.markdown("1. Upload carrier Excel files\n2. Review automatic scores\n3. Approve/Reject manual items\n4. Save changes & Export")
    st.divider()
    st.header("📊 Scoring Tiers")
    st.markdown("🔴 **Tier 1** (Critical): 3x\n\n🟡 **Tier 2** (Important): 2x\n\n🟢 **Tier 3** (Bonus): 1x\n\n⚪ **Unscored**: 0x")
    st.divider()
    if st.button("🗑️ Clear All Data"):
        st.session_state.results = {}
        st.session_state.manual_reviews = {}
        st.session_state.pending_changes = {}
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
        approved = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') == 'approved'])
        rejected = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') == 'rejected'])
        
        ranking_data.append({
            'Carrier': carrier,
            'Services': results.get('service_type', 'Unknown'),
            'Original Score': results.get('total_weighted', 0),
            'Adjusted Score': adjusted['adjusted_weighted'],
            'Adjusted %': adjusted['adjusted_weighted_pct'],
            'Pending': pending,
            'Approved': approved,
            'Rejected': rejected
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
        
        # Show adjusted scores with delta
        raw_delta = adjusted['adjusted_raw'] - res['total_raw']
        weighted_delta = adjusted['adjusted_weighted'] - res['total_weighted']
        c3.metric("Adjusted Raw", f"{adjusted['adjusted_raw']}/{res['max_raw']}", f"{raw_delta:+d} pts" if raw_delta != 0 else "No change")
        c4.metric("Adjusted Weighted", f"{adjusted['adjusted_weighted']}/{res['max_weighted']}", f"{weighted_delta:+d} pts" if weighted_delta != 0 else "No change")
        
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
                    st.markdown(f"**{q_key}**: {q_data['description']} {tier_icon} {tier_label}")
                    st.write(f"Score: **{q_data['raw_score']}/{q_data['max_pts']}** | {q_data['justification']}")
                    if q_data.get('value'):
                        st.caption(f"Response: {q_data['value'][:150]}...")
                    st.divider()

    st.divider()
    st.header("🔍 Manual Review")
    
    # Show summary of review status
    total_items = 0
    pending_count = 0
    approved_count = 0
    rejected_count = 0
    
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
    
    st.markdown(f"""
    **Review Progress:** {approved_count + rejected_count}/{total_items} completed
    - 🟡 Pending: **{pending_count}**
    - 🟢 Approved: **{approved_count}**  
    - 🔴 Rejected: **{rejected_count}**
    """)
    
    st.divider()
    
    items = []
    for carrier, res in st.session_state.results.items():
        for item in res.get('manual_review_items', []):
            key = f"{carrier}_{item['tab']}_{item['question']}"
            status = st.session_state.manual_reviews.get(key, {}).get('status', 'pending')
            # Get tier info
            tier = None
            for tab_key, tab_res in res.get('tabs', {}).items():
                if tab_res['name'] == item['tab']:
                    q_data = tab_res['questions'].get(item['question'], {})
                    tier = q_data.get('tier')
                    break
            items.append({'key': key, 'carrier': carrier, 'status': status, 'tier': tier, **item})

    if items:
        filter_opt = st.selectbox("Filter:", ['All', 'Pending', 'Approved', 'Rejected'])
        filtered = items if filter_opt == 'All' else [i for i in items if i['status'].lower() == filter_opt.lower()]
        
        for item in filtered:
            key = item['key']
            review = st.session_state.manual_reviews.get(key, {})
            current_status = review.get('status', 'pending')
            
            # Status indicator
            if current_status == 'pending':
                status_icon = "🟡"
                status_text = "PENDING"
                status_color = "orange"
            elif current_status == 'approved':
                status_icon = "🟢"
                status_text = "APPROVED"
                status_color = "green"
            else:
                status_icon = "🔴"
                status_text = "REJECTED"
                status_color = "red"
            
            # Calculate score impact
            original_score = item['current_score']
            tier = item.get('tier', 1)
            weighted_impact = original_score * TIER_WEIGHTS.get(tier, 1) if tier else 0
            
            st.markdown(f"### {status_icon} {item['carrier']} | {item['tab']} - {item['question']}")
            
            # Show score impact
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{item['description']}**")
            with col2:
                st.metric("Raw Points", f"{original_score}/{item['max_score']}")
            with col3:
                st.metric("Weighted Impact", f"{weighted_impact} pts", 
                         f"-{weighted_impact}" if current_status == 'rejected' else None,
                         delta_color="inverse" if current_status == 'rejected' else "off")
            
            item_value = item.get('value', '')
            if len(item_value) > 200:
                st.write(f"**Response:** {item_value[:200]}...")
            else:
                st.write(f"**Response:** {item_value}")
            st.caption(f"Review Criteria: {item['review_criteria']}")
            
            # Approve/Reject buttons
            c1, c2, c3 = st.columns([1, 1, 3])
            with c1:
                approve_disabled = current_status == 'approved'
                if st.button("✅ Approve", key=f"a_{key}", disabled=approve_disabled, 
                           use_container_width=True, type="primary" if current_status != 'approved' else "secondary"):
                    st.session_state.manual_reviews[key] = {'status': 'approved', 'score': original_score}
                    st.rerun()
            with c2:
                reject_disabled = current_status == 'rejected'
                if st.button("❌ Reject", key=f"r_{key}", disabled=reject_disabled,
                           use_container_width=True, type="primary" if current_status != 'rejected' else "secondary"):
                    st.session_state.manual_reviews[key] = {'status': 'rejected', 'score': 0}
                    st.rerun()
            with c3:
                if current_status != 'pending':
                    if st.button("↩️ Reset to Pending", key=f"reset_{key}"):
                        st.session_state.manual_reviews[key] = {'status': 'pending', 'score': original_score}
                        st.rerun()
            
            st.divider()
    else:
        st.info("No manual review items.")

    st.divider()
    
    # Export Section
    st.header("📥 Export Results")
    
    # Show final adjusted scores before export
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
            # Rankings with adjusted scores
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
                    review_data.append({
                        'Carrier': carrier,
                        'Section': item['tab'],
                        'Question': item['question'],
                        'Description': item['description'],
                        'Original Score': item['current_score'],
                        'Max Score': item['max_score'],
                        'Decision': review.get('status', 'pending').upper(),
                        'Final Score': review.get('score', item['current_score']) if review.get('status') != 'rejected' else 0
                    })
            if review_data:
                pd.DataFrame(review_data).to_excel(writer, sheet_name='Manual Reviews', index=False)
            
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
                            'Justification': q_data['justification'],
                            'Response': q_data.get('value', '')[:500]
                        })
                pd.DataFrame(data).to_excel(writer, sheet_name=carrier[:31], index=False)
        output.seek(0)
        st.download_button("⬇️ Download Excel Report", output, f"Scorecard_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", 
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("👆 Upload carrier Excel files to get started!")
