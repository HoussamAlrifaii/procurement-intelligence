# Assistant evaluation

20 hand-written cases from `evaluation/assistant_cases.json`; full answers in the matching `assistant_answers*.json`.

| Check | Passed |
|---|---|
| tool | 20/20 (100%) |
| sector | 20/20 (100%) |
| country | 20/20 (100%) |
| grounded | 13/20 (65%) |

| Case | Tool | Sector | Country | Grounded | CPV groups used | Figures not found in tools |
|---|---|---|---|---|---|---|
| network-installer-pl | yes | yes | yes | **no** | 453, 45314, 453143, 4531432 | 350,000 |
| bakery-si | yes | yes | yes | yes | 1581 |  |
| medical-supplies-ro | yes | yes | yes | yes | 3314 |  |
| software-de | yes | yes | yes | yes | 48, 72 |  |
| cleaning-fr | yes | yes | yes | **no** | 9091 | 200,000, 50 |
| road-works-cz | yes | yes | yes | yes | 45233 |  |
| catering-it | yes | yes | yes | yes | 5552 |  |
| translation-eu | yes | yes | yes | yes | 7953 |  |
| furniture-es | yes | yes | yes | **no** | 3911, 39121, 3913 | 10 |
| security-guards-be | yes | yes | yes | yes | 797, 7971 |  |
| lab-equipment-pl | yes | yes | yes | yes | 38 |  |
| bus-transport-se | yes | yes | yes | yes | 34121, 60172 |  |
| architects-nl | yes | yes | yes | **no** | 71 | 1,000,000, 200,000 |
| training-ie | yes | yes | yes | yes | 805 |  |
| price-cabling-pl | yes | yes | yes | **no** | 45314 | 152 |
| price-medicines-ro | yes | yes | yes | yes | 336 |  |
| price-software-de | yes | yes | yes | **no** | 72262 | 140,000 |
| risk-lab-si | yes | yes | yes | yes | 38 |  |
| price-cleaning-fr | yes | yes | yes | **no** | 9091 | 200, 300,000 |
| risk-roads-gr | yes | yes | yes | yes | 45233 |  |
