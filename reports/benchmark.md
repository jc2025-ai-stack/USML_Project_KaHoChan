# Benchmark: Apriori on 1,000,000 baskets

All measurements come from `notebooks/01_mining.ipynb`, run on a Windows 11 laptop with 32 GB of RAM (Python 3.14, mlxtend 0.25).

- **Time:** wall-clock time of the `apriori()` call.
- **Peak memory:** highest memory allocated during the call (`tracemalloc`), on top of the 98 MB basket table already in memory. `tracemalloc` counts virtual memory, so a value above the 32 GB of RAM means Windows moved part of it to the page file on disk.
- **Rules:** `association_rules(metric='confidence', min_threshold=0.2)`, before the lift > 1 filter.

## 1. Wide format (Phase 1)

| Method | Time | Peak memory | Final table |
|---|---|---|---|
| groupby + TransactionEncoder (naive) | 21.5 s | 920 MB | 98 MB |
| factorize + numpy (kept) | 0.71 s | 436 MB | 106 MB |

## 2. Apriori with the default settings (`low_memory=False`)

| min_support | Itemsets | Time | Peak memory | Outcome |
|---|---|---|---|---|
| 0.05 | 191 | 4.5 s | 7,676 MB | OK |
| 0.02 | 658 | 10.2 s | 12,842 MB | OK |
| 0.01 | 2,267 | 43.5 s | 24,682 MB | OK |
| 0.005 | 7,106 | 562.4 s | 108,187 MB | First run: **MemoryError** `Unable to allocate 72.6 GiB for an array with shape (25975, 3, 1000000) and data type bool`. Second run: completed only because Windows grew the page file (31.8 GB → 43.4 GB) and compressed memory; the PC was almost frozen for 9 minutes. |

### Why it fails

- I have executed twice with min_support = 0.005. At the first time, the process raised the memory error when the process needed to allocate 78 GB (72.6 GiB) of RAM for the shape of the data array on a local PC which has only 32 GB of RAM. Then, when I executed for the second time, the PC was close to be frozen while it ran. But after almost 10 mins, the cell stopped and showed the total time spent and the peak memory request of 108 GB.
- I may have fallen into a trap of expecting the memory error at each time the same cell was run. But I kept the honest result of intermittent memory errors which may not occur all the time.
- My guess for the success at the second time is that the Windows OS has managed to use physical memory (RAM) and allocate enough virtual memory as well on the hard drive. So the peak memory appeared to be larger than just the physical memory size. Also, I guess that Windows was able to compress pages of the Apriori's arrays which are mostly false in the True/False table.
- The reason for the peak memory exploding is that the default mode (low_memory = False) checks all candidates at once in one array of shape (candidates, k, baskets); if the shape is (candidates=25975, k=3, baskets=1000000), it means 25,975 triples × 3 × 1,000,000 = about 78 GB. Therefore, lower min_support means more candidates, so memory climbs and time climbs with it too.

### The fix

- The setting of low_memory = True fixes it because it minimizes the amount of memory usage (see the table in section 3).
- **Memory stays almost the same:** The key result is the peak memory size stays almost the same. With low_memory = True, the memory does not depend on the min_support (memory = baskets × products per candidate) because only one candidate is checked at a time; with the default mode, the memory usage is much larger with (memory = candidates × baskets × products per candidate).
- At min_support 0.005, the run takes 26.2 s and 115 MB instead of 562.4 s and 108 GB, with the same 7,106 itemsets.

## 3. Apriori with `low_memory=True`

| min_support | Itemsets | Rules | Time | Peak memory | Outcome |
|---|---|---|---|---|---|
| 0.05 | 191 | 282 | 2.0 s | 112 MB | OK |
| 0.02 | 658 | 3,159 | 4.8 s | 115 MB | OK |
| 0.01 | 2,267 | 9,736 | 11.3 s | 115 MB | OK |
| 0.005 | 7,106 | 28,433 | 26.2 s | 115 MB | OK, **kept for the app** |

At min_support 0.005: 26.2 s and 115 MB with `low_memory=True`, against 562.4 s and 108,187 MB with the default settings.

## 4. Rules kept for the app

min_support 0.005, confidence ≥ 0.2, lift > 1, one product on the THEN side: **11,059 rules** in `models/rules.json`.

## 5. Coverage

**58 of the 98 products (59%) can ever be recommended**, meaning they are the THEN side of at least one rule.

The 40 others are never suggested:
- **5 very rare products** (Safran, Huile de truffe, Caviar, Vinaigre balsamique vieilli, Foie gras, about 0.08% of baskets) fall below the minimum support of 0.5%, so Apriori drops them before building any itemset.
- **35 products are frequent but bought independently** (for example Biscuits, Beurre d'arachide, Fromage cheddar), so no rule suggesting them reaches 20% confidence with lift > 1.

## 6. Two things this approach cannot do

1. **The app ignores the season.** The rules are mined on the whole year, and the recommender only looks at the basket, not the date. In January, a beer buyer is told that customers also buy Charbon de bois 45% of the time, while only 15% of January beer buyers do. The winter-only rules (for example Bière → Bretzels) are missing. **Improvement:** re-mine the rules every season (about 26s with `low_memory=True` in our project) and load the rules file of the current season.
2. **40 of the 98 products can never be recommended.** 5 rare products (about 0.08% of baskets) fall below the minimum support of 0.5%, and 35 frequent products are bought independently, so no rule suggests them. **Improvement:** a fallback for these products, such as the most popular products of the same category, or a separate mining run with a lower min_support for the rare products.
