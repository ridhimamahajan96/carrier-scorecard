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

st.title("🌿 Carrier Sustainability Scorecard")
st.write("Upload carrier survey responses to automatically score and rank sustainability performance")

with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("1. Upload carrier Excel files\n2. Review automatic scores\n3. Approve/Reject/Edit manual items\n4. Export results")
    st.divider()
    st.header("📊 Scoring Tiers")
    st.markdown("🔴 **Tier 1** (Critical): 3x\n\n🟡 **Tier 2** (Important): 2x\n\n🟢 **Tier 3** (Bonus): 1x\n\n⚪ **Unscored**: 0x")
    st.divider()
    if st.button("🗑️ Clear All Data"):
        st.session_state.results = {}
        st.session_state.manual_reviews = {}
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
        pending = len([r for r in results.get('manual_review_items', []) if st.session_state.manual_reviews.get(f"{carrier}_{r['tab']}_{r['question']}", {}).get('status') == 'pending'])
        ranking_data.append({
            'Carrier': carrier,
            'Services': results.get('service_type', 'Unknown'),
            'Raw Score': results.get('total_raw', 0),
            'Weighted Score': results.get('total_weighted', 0),
            'Weighted %': results.get('weighted_percentage', 0),
            'Pending Reviews': pending
        })
    ranking_df = pd.DataFrame(ranking_data).sort_values('Weighted %', ascending=False).reset_index(drop=True)
    ranking_df.index = ranking_df.index + 1
    ranking_df.index.name = 'Rank'
    st.dataframe(ranking_df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(ranking_df, x='Carrier', y='Weighted %', color='Weighted %', color_continuous_scale='Greens', title='Carrier Scores')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(ranking_df, values='Weighted Score', names='Carrier', title='Score Distribution')
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.header("📊 Detailed Analysis")
    selected = st.selectbox("Select carrier:", list(st.session_state.results.keys()))

    if selected:
        res = st.session_state.results[selected]
        c1, c2, c3 = st.columns(3)
        c1.metric("Raw Score", f"{res['total_raw']}/{res['max_raw']}", f"{res['raw_percentage']}%")
        c2.metric("Weighted Score", f"{res['total_weighted']}/{res['max_weighted']}", f"{res['weighted_percentage']}%")
        c3.metric("Services", res.get('service_type', 'Unknown'))

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
    items = []
    for carrier, res in st.session_state.results.items():
        for item in res.get('manual_review_items', []):
            key = f"{carrier}_{item['tab']}_{item['question']}"
            status = st.session_state.manual_reviews.get(key, {}).get('status', 'pending')
            items.append({'key': key, 'carrier': carrier, 'status': status, **item})

    if items:
        filter_opt = st.selectbox("Filter:", ['All', 'Pending', 'Approved', 'Rejected'])
        filtered = items if filter_opt == 'All' else [i for i in items if i['status'].lower() == filter_opt.lower()]
        for item in filtered:
            key = item['key']
            review = st.session_state.manual_reviews.get(key, {})
            icon = "🟡" if review.get('status') == 'pending' else "🟢" if review.get('status') == 'approved' else "🔴"
            st.markdown(f"### {icon} {item['carrier']} | {item['tab']} - {item['question']}")
            st.write(f"**{item['description']}**")
            item_value = item.get('value', '')
            if len(item_value) > 200:
                st.write(f"Response: {item_value[:200]}...")
            else:
                st.write(f"Response: {item_value}")
            st.caption(f"Criteria: {item['review_criteria']} | Auto-score: {item['current_score']}/{item['max_score']}")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("✅ Approve", key=f"a_{key}"):
                st.session_state.manual_reviews[key] = {'status': 'approved', 'score': item['current_score']}
                st.rerun()
            if c2.button("❌ Reject", key=f"r_{key}"):
                st.session_state.manual_reviews[key] = {'status': 'rejected', 'score': 0}
                st.rerun()
            new_score = c3.number_input("Score:", 0, item['max_score'], review.get('score', item['current_score']), key=f"s_{key}")
            if c4.button("💾 Save", key=f"sv_{key}"):
                st.session_state.manual_reviews[key] = {'status': 'edited', 'score': new_score}
                st.rerun()
            st.divider()
    else:
        st.info("No manual review items.")

    st.divider()
    st.header("📥 Export")
    if st.button("📊 Download Excel Report", type="primary"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            ranking_df.to_excel(writer, sheet_name='Rankings')
            for carrier, res in st.session_state.results.items():
                data = []
                for tab_key, tab_res in res.get('tabs', {}).items():
                    for q_key, q_data in tab_res.get('questions', {}).items():
                        data.append({
                            'Section': tab_res['name'],
                            'Question': q_key,
                            'Description': q_data['description'],
                            'Score': q_data['raw_score'],
                            'Max': q_data['max_pts'],
                            'Justification': q_data['justification']
                        })
                pd.DataFrame(data).to_excel(writer, sheet_name=carrier[:31], index=False)
        output.seek(0)
        st.download_button("⬇️ Download", output, f"Scorecard_{datetime.now().strftime('%Y%m%d')}.xlsx")

else:
    st.info("👆 Upload carrier Excel files to get started!")
