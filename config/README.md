# Config
The Django management `build` command uses three config files to customize some
actions that would be impractical to provide as CLI arguments.

1. `custom-refs.json`
2. `disambiguation.cfg`
3. `diambiguation_exceptions.cfg`

## `custom-refs.json`

An object with the following form to allowlist specific RefTypes to be
processes. This is useful for speeding up builds when only a small set of
RefTypes need to be rebuilt.

### Example
```json
{
  "CH": ["Klbkch"],
  "CL": [],
  "LO": [],
  "SK": [],
  "SP": [],
  "IT": []
}
```

The keys correspond to the shortcodes for each of the different categories of
RefTypes: Characters, Classes, Locations, Skills, Spells, and Items.

## `disambiguation.cfg`
There are some common words that are used as legitimate aliases of some
RefTypes. For example "Doctor", "Fool", and "Pawn" all refer to individuals but
may also refer to the general term. This file is a list of words that require
disambiguation from the user during the build process.

### Example
```
Archer
Butler
Doctor
Fool
Pawn
```

## `disambiguation_exceptions.cfg`
Some of the above disambiguations can show up frequently and cause a lot of
prompts when they aren't necessary. This file is a list of word groups that are
known exceptions to the defined disambiguation. This helps reduce the volume of
build prompts.

### Example
```
Crimson eyes
Nomads of the Sky
Red Fang
Red eyes
Shield Spider
Spear Spider
```

TODO: it may be more practical to compose these all into a single JSON or Yaml configuration file.
