# Assistant evaluation

20 hand-written cases from `evaluation/assistant_cases.json`; full answers in `assistant_answers.json`.

| Check | Passed |
|---|---|
| tool | 20/20 (100%) |
| sector | 20/20 (100%) |
| country | 20/20 (100%) |
| grounded | 8/20 (40%) |

| Case | Tool | Sector | Country | Grounded | CPV groups used | Figures not found in tools |
|---|---|---|---|---|---|---|
| network-installer-pl | yes | yes | yes | **no** | 3242, 45314, 72 | 27001, 9001 |
| bakery-si | yes | yes | yes | **no** | 1511 | 1512 |
| medical-supplies-ro | yes | yes | yes | **no** | 331 | 23 |
| software-de | yes | yes | yes | **no** | 48, 72 | 2.07 |
| cleaning-fr | yes | yes | yes | yes | 9091 |  |
| road-works-cz | yes | yes | yes | **no** | 45233 | 40 |
| catering-it | yes | yes | yes | yes | 5552 |  |
| translation-eu | yes | yes | yes | **no** | 792 | 0.9, 10.5, 100, 12.7, 3.1, 300, 803 |
| furniture-es | yes | yes | yes | yes | 3911 |  |
| security-guards-be | yes | yes | yes | **no** | 79 | 34 |
| lab-equipment-pl | yes | yes | yes | yes | 382 |  |
| bus-transport-se | yes | yes | yes | yes | 60 |  |
| architects-nl | yes | yes | yes | **no** | 713 | 1.19 |
| training-ie | yes | yes | yes | yes | 80 |  |
| price-cabling-pl | yes | yes | yes | **no** | 45314 | 238 |
| price-medicines-ro | yes | yes | yes | **no** | 336 | 15 |
| price-software-de | yes | yes | yes | **no** | 720 | 1.2, 735 |
| risk-lab-si | yes | yes | yes | yes | 382 |  |
| price-cleaning-fr | yes | yes | yes | yes | 9091 |  |
| risk-roads-gr | yes | yes | yes | **no** | 45233 | 0.8, 1.2 |
