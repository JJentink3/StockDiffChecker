import streamlit as st
import pandas as pd

st.title("Inventory Comparator: Netsuite vs Deposco")

st.markdown("""
This app allows you to compare inventory levels between two systems: **Netsuite** and **Deposco**.

**How it works:**
- Upload the latest Excel exports from both systems below.
- The app will match products based on EAN and compare the stock levels.
- Differences or missing products will be highlighted.
""")

file_ns = st.file_uploader("Upload Netsuite Excel file", type=["xlsx"])
file_dep = st.file_uploader("Upload Deposco Excel file", type=["xlsx"])

if file_ns and file_dep:
    df_ns = pd.read_excel(file_ns)
    df_dep = pd.read_excel(file_dep)

    # Verwachte kolommen
    ean_col_ns = 'EAN'
    stock_col_ns = 'On Hand'

    ean_col_dep = 'Item EANs (API)'
    stock_col_dep = 'ATP Qty API'

    if not all(col in df_ns.columns for col in [ean_col_ns, stock_col_ns]) or not all(col in df_dep.columns for col in [ean_col_dep, stock_col_dep]):
        st.error("Expected columns were not found in one or both files.")
        st.write("Netsuite columns:", df_ns.columns.tolist())
        st.write("Deposco columns:", df_dep.columns.tolist())
    else:
        st.success(f"Using columns: Netsuite → EAN: '{ean_col_ns}', Stock: '{stock_col_ns}' | Deposco → EAN: '{ean_col_dep}', Stock: '{stock_col_dep}'")

        # Filter Deposco: exclude rows without EAN and those starting with 'Box' or 'Bag'
        df_dep = df_dep[df_dep[ean_col_dep].notna()]
        if 'Number' in df_dep.columns:
            df_dep = df_dep[~df_dep['Number'].astype(str).str.startswith(('Box', 'Bag'))]

        # Rename for merge
        df_ns = df_ns.rename(columns={ean_col_ns: 'EAN', stock_col_ns: 'Stock_NS'})
        df_dep = df_dep.rename(columns={ean_col_dep: 'EAN', stock_col_dep: 'Stock_Deposco'})

        df_ns['EAN'] = df_ns['EAN'].astype(str).str.strip()
        df_dep['EAN'] = df_dep['EAN'].astype(str).str.strip()

        # Merge and compare
        merged = pd.merge(df_ns, df_dep, on='EAN', how='outer', indicator=True)
        merged['Stock_NS'] = merged['Stock_NS'].fillna(0)
        merged['Stock_Deposco'] = merged['Stock_Deposco'].fillna(0)
        merged['Difference'] = merged['Stock_NS'] - merged['Stock_Deposco']

        st.subheader("Inventory Differences")
        difference_df = merged[(merged['Difference'] != 0) | (merged['_merge'] != 'both')]
        st.dataframe(difference_df)

        csv = difference_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Differences as CSV", csv, "inventory_differences.csv", "text/csv")

