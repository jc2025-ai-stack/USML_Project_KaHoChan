# Benchmark: Apriori on 1,000,000 baskets

All measurements come from `notebooks/01_mining.ipynb`, run on a Windows 11 laptop with 32 GB of RAM (Python 3.14, mlxtend 0.25).

- **Time:** wall-clock time of the `apriori()` call.
- **Peak memory:** highest memory allocated during the call (`tracemalloc`), on top of the 98 MB basket table already in memory.
- **Rules:** `association_rules(metric='confidence', min_threshold=0.2)`, before the lift > 1 filter.

## 1. Wide format (Phase 1)

| Method | Time | Peak memory | Final table |
|---|---|---|---|
| groupby + TransactionEncoder (naive) | 20.2 s | 920 MB | 98 MB |
| factorize + numpy (kept) | 0.72 s | 436 MB | 106 MB |

## 2. Apriori with the default settings (`low_memory=False`)

| min_support | Itemsets | Rules | Time | Peak memory | Outcome |
|---|---|---|---|---|---|
| 0.05 | 191 | – | 5.8 s | 7,676 MB | OK, but 70× the memory of `low_memory=True` |
| 0.005 | – | – | – | – | **MemoryError** *(paste the message from the notebook)* |

### Why it fails

*(to be written)*

### The fix

*(to be written)*

## 3. Apriori with `low_memory=True`

| min_support | Itemsets | Rules | Time | Peak memory | Outcome |
|---|---|---|---|---|---|
| 0.05 | 191 | 282 | 2.0 s | 112 MB | OK |
| 0.02 | 658 | 3,159 | 4.7 s | 115 MB | OK |
| 0.01 | 2,267 | 9,736 | 11.0 s | 115 MB | OK |
| 0.005 | 7,106 | 28,433 | 25.1 s | 115 MB | OK, **kept for the app** |

## 4. Rules kept for the app

min_support 0.005, confidence ≥ 0.2, lift > 1, one product on the THEN side: **11,059 rules** in `models/rules.json`.

## 5. Coverage

**58 of the 98 products (59%) can ever be recommended**, meaning they are the THEN side of at least one rule.

The 40 others are never suggested:
- **5 very rare products** (Safran, Huile de truffe, Caviar, Vinaigre balsamique vieilli, Foie gras, about 0.08% of baskets) fall below the minimum support of 0.5%, so Apriori drops them before building any itemset.
- **35 products are frequent but bought independently** (for example Biscuits, Beurre d'arachide, Fromage cheddar), so no rule suggesting them reaches 20% confidence with lift > 1.

## 6. Two things this approach cannot do

1. *(to be written: the limitation, and what to add to fix it)*
2. *(to be written)*
