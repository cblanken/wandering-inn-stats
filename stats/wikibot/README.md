# Wikibot
The wikibot module uses
[pywikibot](https://doc.wikimedia.org/pywikibot/stable/) and
[wikitextparser](https://wikitextparser.readthedocs.io/en/stable/) to process
wiki pages and extract useful information to be imported into the database.

## Pywikibot configuration
Pywikibot requires a [user-config.py](user-config.py)
```python
# Example user-config.py
user_families_paths = ["/home/cam/dev/wandering-inn/stats/wikibot/families"]
mylang = "en"
family = "twi"
password_file= "secrets.py"
```

```python
# Example secrets.py
("MyBot", "long_random_password_here")
```

The TWI wiki is setup to allow anonymous user's to interact, so it's possible
some features of the bot may function without setting up a user. However, to be
considerate to the maintainers of the wiki, a user account should be created so
any bot actions can be tracked.

> [!NOTE]
> It should also be mentioned that any actions made by a bot without a user will
> be recorded via the public IP address of the host running the bot.


## Downloading wiki data
The bot is intended run via the Django management command from the root of the
project.

The primary function of the bot is to download several categories of data from
the wiki. At the time of this writing, the available categories are Characters,
[Skills], [Classes], Spells, Locations and [Artifacts]. They can be selected
with the following commands.

```bash
# The following download to the `./data` directory
python manage.py wikibot --ch ./data    # download Character data
python manage.py wikibot --sk ./data    # download [Skill] data
python manage.py wikibot --cl ./data    # download [Class] data
python manage.py wikibot --sp ./data    # download [Spell] data
python manage.py wikibot --lo ./data    # download Location data
python manage.py wikibot --it ./data    # download [Item]/[Artifact] data

# Alternatively download all categories at once
python manage.py wikibot --all ./data
```

To see help for the bot command run the following.
```
python manage.py wikibot -h
```
