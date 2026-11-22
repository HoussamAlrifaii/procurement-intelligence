# Assistant evaluation

20 hand-written cases from `evaluation/assistant_cases.json`; full answers in `assistant_answers.json`.

| Check | Passed |
|---|---|
| tool | 20/20 (100%) |
| sector | 20/20 (100%) |
| country | 20/20 (100%) |
| grounded | 18/20 (90%) |

| Case | Tool | Sector | Country | Grounded | CPV groups used | Figures not found in tools |
|---|---|---|---|---|---|---|
| network-installer-pl | yes | yes | yes | yes | 3242, 45314, 72 |  |
| bakery-si | yes | yes | yes | yes | 1511 |  |
| medical-supplies-ro | yes | yes | yes | yes | 331 |  |
| software-de | yes | yes | yes | yes | 48, 72 |  |
| cleaning-fr | yes | yes | yes | yes | 9091 |  |
| road-works-cz | yes | yes | yes | yes | 45233 |  |
| catering-it | yes | yes | yes | yes | 5552 |  |
| translation-eu | yes | yes | yes | **no** | 792 | 100, 300,000 |
| furniture-es | yes | yes | yes | yes | 3911 |  |
| security-guards-be | yes | yes | yes | yes | 79 |  |
| lab-equipment-pl | yes | yes | yes | yes | 382 |  |
| bus-transport-se | yes | yes | yes | yes | 60 |  |
| architects-nl | yes | yes | yes | yes | 713 |  |
| training-ie | yes | yes | yes | yes | 80 |  |
| price-cabling-pl | yes | yes | yes | yes | 45314 |  |
| price-medicines-ro | yes | yes | yes | **no** | 336 | 15,000 |
| price-software-de | yes | yes | yes | yes | 720 |  |
| risk-lab-si | yes | yes | yes | yes | 382 |  |
| price-cleaning-fr | yes | yes | yes | yes | 9091 |  |
| risk-roads-gr | yes | yes | yes | yes | 45233 |  |
