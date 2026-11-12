-- standardize_name(name): a simple, explainable company-name key.
--
-- Steps: keep only the first name when several winners are joined with '---',
-- lowercase, remove accents, turn punctuation into spaces, drop common legal
-- form words (GmbH, Ltd, S.A., Sp. z o.o. ...), collapse spaces.
--   'Siemens Healthcare Sp. z o.o.'  -> 'siemens healthcare'
--   'SIEMENS HEALTHCARE, S.L.U.'     -> 'siemens healthcare'
-- The legal-form removal runs twice so that neighbouring forms such as
-- 'GmbH & Co. KG' are all removed (each match consumes the space after it).
--
-- Limits: it does not fix spelling mistakes or translations, and different
-- subsidiaries of one group keep different keys. That is a deliberate choice:
-- a transparent rule is preferred to aggressive matching that could merge
-- unrelated companies.
CREATE OR REPLACE MACRO remove_legal_forms(padded_name) AS
    REGEXP_REPLACE(
        padded_name,
        ' (sp z o o|s r o|s r l|s l u|s p a|s a s|s a|s l|a s|d o o|b v|n v|gmbh|mbh|ag|kg|ohg|ug|ltd|limited|plc|llc|llp|inc|corp|corporation|co|sa|srl|spa|sas|sarl|sl|slu|bv|nv|oy|oyj|ab|as|aps|kft|zrt|nyrt|uab|ou|sia|ooo|eood|ood|ad|doo|se|spzoo) ',
        ' ', 'g'
    );

CREATE OR REPLACE MACRO standardize_name(name) AS
    NULLIF(
        TRIM(
            REGEXP_REPLACE(
                remove_legal_forms(remove_legal_forms(
                    ' ' || REGEXP_REPLACE(
                        STRIP_ACCENTS(LOWER(SPLIT_PART(name, '---', 1))),
                        '[^a-z0-9]+', ' ', 'g'
                    ) || ' '
                )),
                ' +', ' ', 'g'
            )
        ),
        ''
    );

-- yes_no(flag): TED stores yes/no fields as 'Y' / 'N'. Anything else
-- (blank, or several values joined with '---') becomes NULL (unknown).
CREATE OR REPLACE MACRO yes_no(flag) AS
    CASE flag WHEN 'Y' THEN TRUE WHEN 'N' THEN FALSE END;
