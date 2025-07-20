import streamlit as st
import pandas as pd
import io

st.title("Inventory Comparator: Netsuite vs Deposco")

st.markdown("""
This app compares inventory levels between **Netsuite** and **Deposco**.

**Requirements:**
- The **Netsuite** file must contain an `EAN` column and a `On Hand` column.
- The **Deposco** file should be generated as follows:
  - In the Search bar: `:Items`
  - Select the `Item ATP view`
  - Export to Excel

For questions, email: jannes.jentink@postnl.nl
""")

file_ns = st.file_uploader("Upload Netsuite Excel file", type=["xlsx"])
file_dep = st.file_uploader("Upload Deposco Excel file", type=["xlsx"])

def detect_column(columns, keywords):
    matches = [col for col in columns if any(kw.lower() in col.lower() for kw in keywords)]
    if matches:
        return matches[0]
    return None

if file_ns and file_dep:
    df_ns = pd.read_excel(file_ns)
    df_dep = pd.read_excel(file_dep)

    df_ns.columns = df_ns.columns.str.strip()
    df_dep.columns = df_dep.columns.str.strip()

    df_ns = df_ns.loc[:, ~df_ns.columns.duplicated()]
    df_dep = df_dep.loc[:, ~df_dep.columns.duplicated()]

    # Detect relevant columns
    ean_col_ns = detect_column(df_ns.columns, ["ean"])
    stock_col_ns = detect_column(df_ns.columns, ["on hand", "stock", "qty"])

    ean_col_dep = detect_column(df_dep.columns, ["ean"])
    stock_col_dep = detect_column(df_dep.columns, ["atp qty", "stock", "qty"])

    if not ean_col_ns or not ean_col_dep:
        st.error("Could not detect EAN column in both files. Please make sure both files contain an EAN column.")
        st.write("Netsuite columns:", df_ns.columns.tolist())
        st.write("Deposco columns:", df_dep.columns.tolist())
        st.stop()

    if not stock_col_ns or not stock_col_dep:
        st.error("Could not detect stock quantity columns in both files.")
        st.write("Netsuite columns:", df_ns.columns.tolist())
        st.write("Deposco columns:", df_dep.columns.tolist())
        st.stop()

    st.success("Successful comparison made")

    # Clean Deposco file
    df_ns = df_ns.rename(columns={ean_col_ns: "EAN", stock_col_ns: 'Stock_NS'})
    df_dep = df_dep.rename(columns={ean_col_dep: "EAN", stock_col_dep: 'Stock_Deposco'})

    df_dep = df_dep[df_dep['EAN'].notna()]
    item_col_dep = detect_column(df_dep.columns, ["number"])
    if item_col_dep and item_col_dep in df_dep.columns:
        df_dep = df_dep[~df_dep[item_col_dep].astype(str).str.startswith(('Box', 'Bag'))]

    # Clean match key values
    df_ns['EAN'] = df_ns['EAN'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    df_dep['EAN'] = df_dep['EAN'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    # Detect optional columns
    desc_col_ns = detect_column(df_ns.columns, ["description"])
    desc_col_dep = detect_column(df_dep.columns, ["description"])
    item_col_ns = detect_column(df_ns.columns, ["item"])

    if desc_col_dep:
        df_dep = df_dep.rename(columns={desc_col_dep: 'Description'})
    elif desc_col_ns:
        df_ns = df_ns.rename(columns={desc_col_ns: 'Description'})

    if item_col_ns:
        df_ns = df_ns.rename(columns={item_col_ns: 'Item'})

    # Merge datasets
    cols_ns = ['EAN', 'Stock_NS']
    if 'Item' in df_ns.columns: cols_ns.append('Item')
    if 'Description' in df_ns.columns: cols_ns.append('Description')

    cols_dep = ['EAN', 'Stock_Deposco']
    if 'Description' in df_dep.columns: cols_dep.append('Description')

    df_ns = df_ns[[col for col in cols_ns if col in df_ns.columns]]
    df_dep = df_dep[[col for col in cols_dep if col in df_dep.columns]]

    merged = pd.merge(df_ns, df_dep, on='EAN', how='outer', indicator=True)

    merged['Stock_NS'] = merged['Stock_NS'].fillna(0)
    merged['Stock_Deposco'] = merged['Stock_Deposco'].fillna(0)
    merged['Difference'] = merged['Stock_NS'] - merged['Stock_Deposco']

    # Prepare final output
    display_cols = ['EAN', 'Item', 'Description', 'Stock_NS', 'Stock_Deposco', 'Difference']
    difference_df = merged[(merged['Difference'] != 0) | (merged['_merge'] != 'both')]
    difference_df = difference_df[[col for col in display_cols if col in difference_df.columns]]

    st.subheader("Inventory Differences")
    st.dataframe(difference_df)

    # Summary statistics
    st.markdown(f"**Total discrepancies found:** {len(difference_df)}")

    # Export to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        difference_df.to_excel(writer, index=False, sheet_name='Differences')
    output.seek(0)

    st.download_button("Download Differences as Excel", output, file_name="inventory_differences.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
