# Innverse Stats

A web app for searching The Wandering Inn web serial and exploring interesting statistics of the
many characters, [Skills], [Classes], [Spells], etc.

Check out the live site at [https://twi-stats.cblanken.dev](https://twi-stats.cblanken.dev)

## Development

### Install dependencies

The project dependencies are managed with [uv](https://astral.sh/uv/). To install all the project
dependencies simply run `uv sync`.

Please be aware, that if you receive build errors from the
[psycopg](https://github.com/psycopg/psycopg) dependency when running `uv sync`. Then you may need
to install the [Clang compiler](https://clang.llvm.org) to build it. Re-run uv while specifi the
compiler with `CC` env variable like so: `CC=clang uv sync`.

If you cannot install Clang for any reason, then you may modify the appropriate line in
`pyproject.toml`. Instead of `psycopg[c,pool]<4.0,>=3.3`, replace the `c` extra with `binary` like
so: `psycopg[binary,pool]<4.0,>=3.3`, of course leaving the version numbers as defined. The binary
version of psycopg is not recommended for production use but is good enough for development and will
not require you to compile it locally.

### Datbase setup

The application requires a Postgres database. The easiest way to get one up and running is with
docker.

```
docker run -p 5432:5432 --name twi-stats-db -e POSTGRES_PASSWORD=password -e POSTGRES_DB=innverse -d postgres
```

This will setup a Postgres database instance via docker with the correct database name. Of course,
feel free to use a different password, port, and container name.

You also need to run the `prepare_db.sql` script to setup some custom configurations for the
database which cannot be setup automatically by the Django app. Source your .env file and execute
the SQL script in the database. You may also provide the parameters manually if you can't source the
.env for some reason.

```shell
source .env
psql -h $TWI_DB_HOST -p $TWI_DB_PORT -U $TWI_DB_USER -f scripts/prepare_db.sql innverse
```

### Environment

The application requires a few important environment variables on startup.

| Variable           | Description                                                      |
| ------------------ | ---------------------------------------------------------------- |
| TWI_ADMIN_EMAIL    | Admin email                                                      |
| TWI_ADMIN_NAME     | Name of the admin user                                           |
| TWI_ANALYTICS_ID   | Umami analytics ID (optional)                                    |
| TWI_DB_HOST        | Database host (default: localhost)                               |
| TWI_DB_PASS        | Database pasword (default: password)                             |
| TWI_DB_PORT        | Database port (default: 5432)                                    |
| TWI_DB_USER        | Database user (default: postgres)                                |
| TWI_DEBUG          | Enable/disable app debug mode (defaults to off)                  |
| TWI_DISABLE_CACHE  | Enable/deisable app caching. Useful for debugging.               |
| TWI_KEY            | Application security key, this should bea long randomized string |
| TWI_PROD           | Enable production mode                                           |
| TWI_PUBLIC_HOST    | The public hostname. Required if hosting publicly on a domain.   |
| PYWIKIBOT_DIR      | Directory for TWI wiki bot source (should be "stats/wikibot")    |
| PYWIKIBOT_USER     | TWI Wiki bot username (no default)                               |
| PYWIKIBOT_BOT_NAME | Name of the TWI wiki bot (no default)                            |
| PYWIKIBOT_PASS     | Password for the TWI wiki bot (no default)                       |

For your initial setup, simply copy the `.env.example` file in the project root to `.env` and adjust
any values as needed.

# License

- Copyright of The Wandering Inn and all original text belongs to
  [pirateaba](https://www.patreon.com/pirateaba).
- All other code falls under the MIT [LICENSE](LICENSE).

## Credits

- See [The Wandering Inn offical website](https://wanderinginn.com) to check out the web serial
  which inspired this project, and check out the author's
  [Patreon](https://www.patreon.com/pirateaba) if you enjoy the web serial and would like to support
  them.
- Thanks to the wonderful [Wiki Warriors] over on the [TWI Wiki](https://wiki.wanderinginn.com)
  responsible for cataloguing all the various characters, locations, [Skills], [Classes], [Spells]
  etc. without which this project would not have been possible.
