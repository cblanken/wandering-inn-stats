-- This script prepares the DB and should only be run ONCE before the initial application of
-- migrations via `python manage.py migrate`.

-- Remove custom text search dictionary if it exists
DROP TEXT SEARCH DICTIONARY IF EXISTS english_stem_nostop CASCADE;

-- Create english text search dictionary with stems but without stop words
CREATE TEXT SEARCH DICTIONARY english_stem_nostop (Template = snowball, Language = english);
CREATE TEXT SEARCH CONFIGURATION pg_catalog.english_nostop (COPY = pg_catalog.english);
ALTER TEXT SEARCH CONFIGURATION pg_catalog.english_nostop
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, hword, hword_part, word
    WITH english_stem_nostop;
