import streamlit as st
import pandas as pd
import io

st.title("Inventory Comparator: Netsuite vs Deposco")

st.markdown("""
This app allows you to compare inventory levels between two systems: **Netsuite** and **Deposco**.

**Requirements:**
- **Netsuite** file must contain an EAN column and a stock column (e.g., `On Hand`).
- **Deposco** file should be generated as follows:
  - In the Search bar: `Search :Items`
  - Select the `Item ATP view`
  - Export to Excel

The app matches items based on **EAN**, or falls back to **Item** if no EAN is found.

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
    item_col_ns = detect_column(df_ns.columns, ["item"])
    stock_col_ns = detect_column(df_ns.columns, ["on hand", "stock", "qty"])

    ean_col_dep = detect_column(df_dep.columns, ["ean"])
    item_col_dep = detect_column(df_dep.columns, ["number"])
    stock_col_dep = detect_column(df_dep.columns, ["atp qty", "stock", "qty"])

    # Determine matching key
    if ean_col_ns and ean_col_dep:
        match_key = "EAN"
        df_ns = df_ns.rename(columns={ean_col_ns: match_key})
        df_dep = df_dep.rename(columns={ean_col_dep: match_key})
    elif item_col_ns and item_col_dep:
        match_key = "Item"
        if item_col_ns != match_key:
            df_ns = df_ns.rename(columns={item_col_ns: match_key})
        if item_col_dep != match_key:
            df_dep = df_dep.rename(columns={item_col_dep: match_key})
    else:
        st.error("Could not detect matching key (EAN or Item) in both files.")
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
    if match_key == "EAN":
        df_dep = df_dep[df_dep[match_key].notna()]
    if item_col_dep and item_col_dep in df_dep.columns:
        df_dep = df_dep[~df_dep[item_col_dep].astype(str).str.startswith(('Box', 'Bag'))]

    df_ns = df_ns.rename(columns={stock_col_ns: 'Stock_NS'})
    df_dep = df_dep.rename(columns={stock_col_dep: 'Stock_Deposco'})

    # Clean match key values
    df_ns[match_key] = df_ns[match_key].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    df_dep[match_key] = df_dep[match_key].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    # Detect optional columns
    desc_col_ns = detect_column(df_ns.columns, ["description"])
    desc_col_dep = detect_column(df_dep.columns, ["description"])

    if desc_col_dep:
        df_dep = df_dep.rename(columns={desc_col_dep: 'Description'})
    elif desc_col_ns:
        df_ns = df_ns.rename(columns={desc_col_ns: 'Description'})

    # Merge datasets
    cols_ns = [match_key, 'Stock_NS']
    if 'Item' in df_ns.columns: cols_ns.append('Item')
    if 'Description' in df_ns.columns: cols_ns.append('Description')

    cols_dep = [match_key, 'Stock_Deposco']
    if 'Description' in df_dep.columns: cols_dep.append('Description')

    df_ns = df_ns[[col for col in cols_ns if col in df_ns.columns]]
    df_dep = df_dep[[col for col in cols_dep if col in df_dep.columns]]

    merged = pd.merge(df_ns, df_dep, on=match_key, how='outer', indicator=True)

    merged['Stock_NS'] = merged['Stock_NS'].fillna(0)
    merged['Stock_Deposco'] = merged['Stock_Deposco'].fillna(0)
    merged['Difference'] = merged['Stock_NS'] - merged['Stock_Deposco']

    # Prepare final output
    display_cols = [match_key, 'Item', 'Description', 'Stock_NS', 'Stock_Deposco', 'Difference']
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
