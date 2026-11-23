# Assistant evaluation

20 hand-written cases from `evaluation/assistant_cases.json`; full answers in `assistant_answers.json`.

| Check | Passed |
|---|---|
| tool | 20/20 (100%) |
| sector | 20/20 (100%) |
| country | 20/20 (100%) |
| grounded | 14/20 (70%) |

| Case | Tool | Sector | Country | Grounded | CPV groups used | Figures not found in tools |
|---|---|---|---|---|---|---|
| network-installer-pl | yes | yes | yes | yes | 3242, 453, 453143, 4531432, 72 |  |
| bakery-si | yes | yes | yes | yes | 1581 |  |
| medical-supplies-ro | yes | yes | yes | yes | 3314 |  |
| software-de | yes | yes | yes | yes | 48, 72 |  |
| cleaning-fr | yes | yes | yes | **no** | 9091 | 100, 200,000 |
| road-works-cz | yes | yes | yes | yes | 45233 |  |
| catering-it | yes | yes | yes | **no** | 5552 | 40.8 |
| translation-eu | yes | yes | yes | yes | 794 |  |
| furniture-es | yes | yes | yes | yes | 391, 3913 |  |
| security-guards-be | yes | yes | yes | **no** | 797, 7971, 79713 | 500,000 |
| lab-equipment-pl | yes | yes | yes | yes | 38 |  |
| bus-transport-se | yes | yes | yes | yes | 6013, 6014, 6017 |  |
| architects-nl | yes | yes | yes | **no** | 711, 712, 713 | 200,000, 3,000,000 |
| training-ie | yes | yes | yes | yes | 80 |  |
| price-cabling-pl | yes | yes | yes | yes | 453143 |  |
| price-medicines-ro | yes | yes | yes | **no** | 336 | 45 |
| price-software-de | yes | yes | yes | **no** | 72262 | 150,000 |
| risk-lab-si | yes | yes | yes | yes | 38437 |  |
| price-cleaning-fr | yes | yes | yes | yes | 9091 |  |
| risk-roads-gr | yes | yes | yes | yes | 45233 |  |
