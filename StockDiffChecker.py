import streamlit as st
import pandas as pd
import io

st.title("Inventory Comparator: Netsuite vs Deposco")

st.markdown("""
This app allows you to compare inventory levels between two systems: **Netsuite** and **Deposco**.

**How it works:**
- Upload the latest Excel exports from both systems below.
- The app will match products based on EAN and compare the stock levels.
- Output is a file showcasing differences in stock between the two systems.
- For questions, email: jannes.jentink@postnl.nl

ℹ️ Make sure the files contain the following columns:
- **Netsuite**: a column containing the EAN (e.g., `EAN`) and a stock column (e.g., `On Hand`)
- **Deposco**: a column with EANs (e.g., `Item EANs (API)`) and available stock (e.g., `ATP Qty API`)
""")

file_ns = st.file_uploader("Upload Netsuite Excel file", type=["xlsx"])
file_dep = st.file_uploader("Upload Deposco Excel file", type=["xlsx"])

def detect_column(columns, keywords):
    for col in columns:
        for kw in keywords:
            if kw.lower() in col.lower():
                return col
    return None

if file_ns and file_dep:
    df_ns = pd.read_excel(file_ns)
    df_dep = pd.read_excel(file_dep)

    # Kolomdetectie
    ean_col_ns = detect_column(df_ns.columns, ["ean"])
    stock_col_ns = detect_column(df_ns.columns, ["on hand", "stock", "qty"])

    ean_col_dep = detect_column(df_dep.columns, ["ean"])
    stock_col_dep = detect_column(df_dep.columns, ["atp qty", "stock", "qty"])

    if not all([ean_col_ns, stock_col_ns, ean_col_dep, stock_col_dep]):
        st.error("Could not automatically detect required columns. Please ensure EAN and stock quantity columns are present.")
        st.write("Netsuite columns:", df_ns.columns.tolist())
        st.write("Deposco columns:", df_dep.columns.tolist())
    else:
        st.success("Successful comparison made")

        # Filter Deposco: exclude rows without EAN and those starting with 'Box' or 'Bag'
        df_dep = df_dep[df_dep[ean_col_dep].notna()]
        if 'Number' in df_dep.columns:
            df_dep = df_dep[~df_dep['Number'].astype(str).str.startswith(('Box', 'Bag'))]

        # Rename for merge
        df_ns = df_ns.rename(columns={ean_col_ns: 'EAN', stock_col_ns: 'Stock_NS'})
        df_dep = df_dep.rename(columns={ean_col_dep: 'EAN', stock_col_dep: 'Stock_Deposco'})

        df_ns['EAN'] = df_ns['EAN'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df_dep['EAN'] = df_dep['EAN'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

        # Optional: choose item + description columns
        item_col = detect_column(df_ns.columns, ["item"])
        desc_col_ns = detect_column(df_ns.columns, ["description"])
        desc_col_dep = detect_column(df_dep.columns, ["description"])

        if item_col: df_ns = df_ns.rename(columns={item_col: 'Item'})
        if desc_col_dep:
            df_dep = df_dep.rename(columns={desc_col_dep: 'Description'})
        elif desc_col_ns:
            df_ns = df_ns.rename(columns={desc_col_ns: 'Description'})

        # Merge and compare
        merged = pd.merge(
            df_ns[['EAN', 'Item', 'Description', 'Stock_NS']] if 'Item' in df_ns.columns and 'Description' in df_ns.columns else df_ns,
            df_dep[['EAN', 'Description', 'Stock_Deposco']] if 'Description' in df_dep.columns else df_dep,
            on='EAN', how='outer', indicator=True
        )

        merged['Stock_NS'] = merged['Stock_NS'].fillna(0)
        merged['Stock_Deposco'] = merged['Stock_Deposco'].fillna(0)
        merged['Difference'] = merged['Stock_NS'] - merged['Stock_Deposco']

        # Only keep the columns we want
        display_cols = ['EAN', 'Item', 'Description', 'Stock_NS', 'Stock_Deposco', 'Difference']
        difference_df = merged[(merged['Difference'] != 0) | (merged['_merge'] != 'both')]
        difference_df = difference_df[[col for col in display_cols if col in difference_df.columns]]

        st.subheader("Inventory Differences")
        st.dataframe(difference_df)

        # Export to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            difference_df.to_excel(writer, index=False, sheet_name='Differences')
        output.seek(0)

        st.download_button("Download Differences as Excel", output, file_name="inventory_differences.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
