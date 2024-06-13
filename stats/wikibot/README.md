The wikibot module uses [pywikibot]() and [wikitextparser]() to process wiki pages and extract
useful information to be imported into the [database]()

## Pywikibot
Pywikibot requires a [user-config.py]()
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
