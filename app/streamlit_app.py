'''
Boréal Marché - recommendation app.

The rules were mined OFFLINE by notebooks/01_mining.ipynb and saved to models/.
This app only LOADS those files: it never calls Apriori.

Run from the repository root:
    streamlit run app/streamlit_app.py
'''
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent   # repository root (the folder that contains app/, models/, data/)

st.set_page_config(page_title='Boréal Marché', layout='wide')


# ---------- Load the files (only once, then kept in cache) ----------
@st.cache_data
def load_files():
    rules = json.loads((ROOT / 'models' / 'rules.json').read_text(encoding='utf-8'))
    metadata = json.loads((ROOT / 'models' / 'metadata.json').read_text(encoding='utf-8'))
    products = pd.read_csv(ROOT / 'data' / 'products.csv').set_index('Item')   # Item = French name, used in the rules
    return rules, metadata, products


rules, metadata, products = load_files()
min_support = metadata['thresholds']['min_support']
n_baskets = metadata['data']['baskets']
items_in_rules = {item for rule in rules for item in rule['antecedents'] + [rule['consequent']]}


# ---------- Recommendation engine ----------
def recommend(basket, how_many=5):
    '''
    Returns (suggestions, fired)
    - fired: the rules whose IF products are ALL in the basket, and whose THEN product is not in the basket yet
    - suggestions: one rule per suggested product (the one with the highest lift), sorted by lift, at most how_many
    '''
    basket = set(basket)
    fired = []
    best = {}   # product -> best rule for that product

    for rule in rules:
        if not set(rule['antecedents']).issubset(basket):   # subset matching: every IF product must be in the basket
            continue
        product = rule['consequent']
        if product in basket:                               # never suggest a product already in the basket
            continue
        fired.append(rule)
        if product not in best or rule['lift'] > best[product]['lift']:   # two rules, same product: keep the higher lift
            best[product] = rule

    suggestions = sorted(best.values(), key=lambda rule: rule['lift'], reverse=True)[:how_many]
    return suggestions, fired


def strength(lift):
    # label derived from the lift
    if lift >= 6:
        return 'very strong'
    if lift >= 3:
        return 'strong'
    if lift >= 1.5:
        return 'moderate'
    return 'weak'


def show_popular(basket):
    # fallback: the 5 most frequent products that are not in the basket yet
    popular = sorted(metadata['item_support'].items(), key=lambda pair: pair[1], reverse=True)
    popular = [(item, support) for item, support in popular if item not in basket][:5]
    st.write('**Most popular products:**')
    for item, support in popular:
        st.write(f'- {item} ({products.loc[item, "Item_EN"]}) — in {support:.1%} of baskets')


# ---------- Basket (kept between clicks in session_state) ----------
if 'basket' not in st.session_state:
    st.session_state.basket = []
basket = st.session_state.basket

suggestions, fired = recommend(basket)
total = products.loc[basket, 'Price'].sum()

# ---------- Header ----------
st.title('Boréal Marché — Recommendation Engine')
st.caption(f'Apriori association rules mined offline on {metadata["mining_date"]} '
           f'from {n_baskets:,} baskets, loaded from models/rules.json')

col1, col2, col3, col4 = st.columns(4)
col1.metric('Rules loaded', f'{len(rules):,}')
col2.metric('Products', len(products))
col3.metric('Items in basket', len(basket))
col4.metric('Basket total', f'{total:.2f} $')

zone1, zone2, zone3 = st.columns(3)

# ---------- Zone 1: Catalogue ----------
with zone1:
    st.header('1 · Catalogue')
    category = st.selectbox('Category', ['All'] + sorted(products['Category'].unique()))
    search = st.text_input('Search by name')

    shown = products
    if category != 'All':
        shown = shown[shown['Category'] == category]
    if search:
        shown = shown[shown.index.str.contains(search, case=False, regex=False)
                      | shown['Item_EN'].str.contains(search, case=False, regex=False)]
    st.caption(f'{len(shown)} product(s)')

    with st.container(height=500):   # scrollable list
        for item, row in shown.iterrows():
            left, right = st.columns([3, 1])
            left.write(f'**{item}** ({row["Item_EN"]})  \n{row["Category"]} · {row["Price"]:.2f} $')
            if right.button('Add', key='add_' + item, disabled=item in basket):
                basket.append(item)
                st.rerun()

# ---------- Zone 2: Basket ----------
with zone2:
    st.header('2 · My basket')
    if not basket:
        st.info('The basket is empty. Add a product to see recommendations.')

    for item in basket:
        row = products.loc[item]
        left, right = st.columns([3, 1])
        left.write(f'**{item}**  \n{row["Category"]} · {row["Price"]:.2f} $')
        if right.button('Remove', key='remove_' + item):
            basket.remove(item)
            st.rerun()

    if basket:
        st.write(f'**Total: {total:.2f} $**')
        if st.button('Clear basket'):
            basket.clear()
            st.rerun()

    # edge case: a product that appears in no rule at all (very rare, or bought independently)
    for item in basket:
        if item not in items_in_rules:
            support = metadata['item_support'][item]
            if support < min_support:
                st.warning(f'{item} is in only {support:.2%} of baskets, below the minimum support of {min_support:.1%}. '
                           f'Apriori removes it before building any rule, so it appears in no rule at all.')
            else:
                st.warning(f'{item} is in {support:.1%} of baskets but is bought independently of other products, '
                           f'so no rule with lift > 1 contains it.')

# ---------- Zone 3: Recommendations ----------
with zone3:
    st.header('3 · You may also like')

    if not basket:                     # edge case: empty basket
        st.info('No rule can fire on an empty basket (cold start). Showing the most popular products instead.')
        show_popular(basket)
    elif not suggestions:              # edge case: no rule fires
        st.warning('No rule fires for this basket. Showing the most popular products instead.')
        show_popular(basket)

    for rule in suggestions:
        item = rule['consequent']
        row = products.loc[item]
        with st.container(border=True):
            st.write(f'**{item}** ({row["Item_EN"]}) — {row["Category"]} · {row["Price"]:.2f} $')
            st.write(f'Because your basket contains **{", ".join(rule["antecedents"])}**, customers who buy that '
                     f'also buy **{item}** {rule["confidence"]:.0%} of the time — that is '
                     f'{rule["lift"]:.1f}× more often than average.')
            st.write(f'Support {rule["support"]:.2%} · Confidence {rule["confidence"]:.1%} · '
                     f'Lift {rule["lift"]:.2f} · **{strength(rule["lift"])} association**')

# ---------- Rules that fired (makes every suggestion explainable) ----------
with st.expander('Rules that fired'):
    st.write(f'{len(fired)} rule(s) fired for this basket. The rules behind the suggestions shown:')
    table = pd.DataFrame({
        'If the basket contains': [' + '.join(rule['antecedents']) for rule in suggestions],
        'Then suggest': [rule['consequent'] for rule in suggestions],
        'Support': [f'{rule["support"]:.2%}' for rule in suggestions],
        'Confidence': [f'{rule["confidence"]:.1%}' for rule in suggestions],
        'Lift': [round(rule['lift'], 2) for rule in suggestions],
    })
    st.dataframe(table, hide_index=True)
