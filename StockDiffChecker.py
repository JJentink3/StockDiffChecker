import streamlit as st
import pandas as pd

st.title("Inventory Comparator: Netsuite vs Deposco")

st.markdown("""
This app allows you to compare inventory levels between two systems: **Netsuite** and **Deposco**.

**How it works:**
- Upload the latest Excel exports from both systems below.
- The app will automatically match products based on the EAN (detected by any column containing 'EAN' or 'EANs' in the name).
- Differences in stock levels or missing products will be highlighted.
""")

file_ns = st.file_uploader("Upload Netsuite Excel file", type=["xlsx"])
file_dep = st.file_uploader("Upload Deposco Excel file", type=["xlsx"])

if file_ns and file_dep:
    df_ns = pd.read_excel(file_ns)
    df_dep = pd.read_excel(file_dep)

    # Automatically detect EAN and stock columns
    ean_col_ns = next((col for col in df_ns.columns if 'ean' in col.lower()), None)
    stock_col_ns = next((col for col in df_ns.columns if 'qty' in col.lower() or 'stock' in col.lower()), None)

    ean_col_dep = next((col for col in df_dep.columns if 'ean' in col.lower()), None)
    stock_col_dep = next((col for col in df_dep.columns if 'on hand' in col.lower() or 'stock' in col.lower()), None)

    if not all([ean_col_ns, stock_col_ns, ean_col_dep, stock_col_dep]):
        st.error("Could not automatically detect EAN or stock columns. Please check your files.")
        st.write("Detected Netsuite columns:", df_ns.columns.tolist())
        st.write("Detected Deposco columns:", df_dep.columns.tolist())
    else:
        st.success(f"Using columns: Netsuite → EAN: '{ean_col_ns}', Stock: '{stock_col_ns}' | Deposco → EAN: '{ean_col_dep}', Stock: '{stock_col_dep}'")

        # Filter Netsuite: exclude rows without EAN and those starting with 'Box' or 'Bag'
        df_ns = df_ns[df_ns[ean_col_ns].notna()]
        if 'Number' in df_ns.columns:
            df_ns = df_ns[~df_ns['Number'].astype(str).str.startswith(('Box', 'Bag'))]

        # Rename columns for consistency
        df_ns = df_ns.rename(columns={ean_col_ns: 'EAN', stock_col_ns: 'Stock_NS'})
        df_dep = df_dep.rename(columns={ean_col_dep: 'EAN', stock_col_dep: 'Stock_Deposco'})

        # Ensure EAN is string
        df_ns['EAN'] = df_ns['EAN'].astype(str).str.strip()
        df_dep['EAN'] = df_dep['EAN'].astype(str).str.strip()

        # Merge on EAN
        merged = pd.merge(df_ns, df_dep, on='EAN', how='outer', indicator=True)

        # Calculate stock difference
        merged['Stock_NS'] = merged['Stock_NS'].fillna(0)
        merged['Stock_Deposco'] = merged['Stock_Deposco'].fillna(0)
        merged['Difference'] = merged['Stock_NS'] - merged['Stock_Deposco']

        # Show differences
        st.subheader("Inventory Differences")
        difference_df = merged[(merged['Difference'] != 0) | (merged['_merge'] != 'both')]
        st.dataframe(difference_df)

        # Option to download results
        csv = difference_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Differences as CSV", csv, "inventory_differences.csv", "text/csv")
