import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import io

st.set_page_config(page_title="Fuzzy Matcher", page_icon="🔍", layout="wide")

st.title("🔍 Fuzzy String Matcher")
st.markdown("Upload a CSV file to match items from a main column against a target column.")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

if uploaded_file is not None:
    # Read the CSV
    df = pd.read_csv(uploaded_file)
    
    st.subheader("Preview of uploaded data")
    st.dataframe(df.head(), use_container_width=True)
    
    # Column selection
    st.subheader("Select columns")
    col1, col2 = st.columns(2)
    
    with col1:
        main_column = st.selectbox(
            "Main column (items to match)", 
            df.columns, 
            key="main_col",
            help="Each item in this column will be matched against all items in the target column"
        )
    
    with col2:
        target_column = st.selectbox(
            "Target column (search pool)", 
            df.columns, 
            key="target_col",
            help="This column will be searched to find matches for each main column item"
        )
    
    # Matching method selection
    st.subheader("Fuzzy matching settings")
    match_method = st.selectbox(
        "Select matching algorithm",
        ["Ratio", "Partial Ratio", "Token Sort Ratio", "Token Set Ratio"],
        help="Different algorithms for string comparison. 'Ratio' is standard, 'Partial Ratio' finds substrings, 'Token Sort/Set' ignore word order."
    )
    
    threshold = st.slider(
        "Match threshold (%)",
        min_value=0,
        max_value=100,
        value=80,
        help="Scores above this threshold will be marked as a match"
    )
    
    if st.button("Run Fuzzy Match", type="primary"):
        # Get unique non-null values from both columns
        main_items = df[main_column].dropna().astype(str).tolist()
        target_items = df[target_column].dropna().astype(str).unique().tolist()
        
        st.info(f"Matching {len(main_items)} items from main column against {len(target_items)} unique items in target column...")
        
        # Perform fuzzy matching for each main item
        results = []
        
        # Progress bar (outside spinner so it updates properly)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, main_item in enumerate(main_items):
            best_match = None
            best_score = 0
            
            # Compare against all target items
            for target_item in target_items:
                # Calculate similarity score based on selected method
                if match_method == "Ratio":
                    score = fuzz.ratio(main_item, target_item)
                elif match_method == "Partial Ratio":
                    score = fuzz.partial_ratio(main_item, target_item)
                elif match_method == "Token Sort Ratio":
                    score = fuzz.token_sort_ratio(main_item, target_item)
                else:  # Token Set Ratio
                    score = fuzz.token_set_ratio(main_item, target_item)
                
                # Keep track of best match
                if score > best_score:
                    best_score = score
                    best_match = target_item
            
            # Determine if it's a match based on threshold
            is_match = best_score >= threshold
            
            results.append({
                'Main Item': main_item,
                'Best Match': best_match if best_match else "No match found",
                'Confidence (%)': best_score,
                'Match Status': 'Match' if is_match else 'No Match'
            })
            
            # Update progress
            progress = (idx + 1) / len(main_items)
            progress_bar.progress(progress)
            status_text.text(f"Processing: {idx + 1}/{len(main_items)} items ({progress*100:.1f}%)")
        
        progress_bar.empty()
        status_text.empty()
        
        result_df = pd.DataFrame(results)
        
        # Store results in session state
        st.session_state.result_df = result_df
        st.success("✅ Matching complete!")
    
    # Display results if they exist in session state (moved outside button block)
    if 'result_df' in st.session_state:
        result_df = st.session_state.result_df
        
        # Display results
        st.subheader("Matching Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", len(result_df))
        with col2:
            matches = len(result_df[result_df['Match Status'] == 'Match'])
            st.metric("Matches Found", matches)
        with col3:
            no_matches = len(result_df[result_df['Match Status'] == 'No Match'])
            st.metric("No Matches", no_matches)
        with col4:
            avg_confidence = result_df['Confidence (%)'].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.1f}%")
        
        # Filter options
        st.subheader("Filter Results")
        filter_option = st.radio(
            "Show:",
            ["All", "Matches Only", "No Matches Only"],
            horizontal=True,
            key="filter_radio"
        )
        
        if filter_option == "Matches Only":
            display_df = result_df[result_df['Match Status'] == 'Match']
        elif filter_option == "No Matches Only":
            display_df = result_df[result_df['Match Status'] == 'No Match']
        else:
            display_df = result_df
        
        # Display full results with color coding
        if len(display_df) > 0:
            st.dataframe(
                display_df.style.map(
                    lambda x: 'background-color: #90EE90' if x == 'Match' else ('background-color: #FFB6C6' if x == 'No Match' else ''),
                    subset=['Match Status']
                ).background_gradient(subset=['Confidence (%)'], cmap='RdYlGn', vmin=0, vmax=100),
                use_container_width=True,
                height=400
            )
        else:
            st.warning("No results match the selected filter.")
        
        # Download results
        csv_buffer = io.StringIO()
        result_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv_data,
            file_name="fuzzy_match_results.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Please upload a CSV file to get started")
    
    # Example format
    with st.expander("ℹ️ How it works"):
        st.markdown("""
        **This tool performs fuzzy matching between two columns:**
        
        1. **Main Column**: Your reference list (e.g., customer names, product names)
        2. **Target Column**: The pool to search through for matches
        
        **For each item in the main column**, the tool will:
        - Compare it against ALL items in the target column
        - Find the best match
        - Return the confidence level (0-100%)
        
        **Example:**
        
        | Main Column | Target Column |
        |-------------|---------------|
        | Apple Inc. | Apple Incorporated |
        | Microsoft Corp | Microsoft Corporation |
        | Google LLC | Amazon Web Services |
        |  | Alphabet Inc |
        
        **Result:**
        
        | Main Item | Best Match | Confidence | Status |
        |-----------|------------|------------|--------|
        | Apple Inc. | Apple Incorporated | 95% | Match |
        | Microsoft Corp | Microsoft Corporation | 92% | Match |
        | Google LLC | Alphabet Inc | 65% | No Match |
        
        **Note**: The columns can have different lengths!
        """)

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    "This app uses fuzzy string matching to find the best match for each item "
    "in your main column by searching through all items in the target column. "
    "Perfect for matching customer names, product lists, or any text data!"
)