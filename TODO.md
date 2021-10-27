Active:
- move to pkm

Backlog:
- Rework configuration (remove cache-dir, add alternative?) make hierarchical
- remove layout
- remove installer and add env managers (+self env)
- move toml namespace from poetry to pkm
- improve init to support poetry and pipenv
- universal sources + conda, commands, repositories
- consider dropping plugins support
- add build-scripts/tasks section makefile style
- add recipes in the documentation
- investigate - why so slow `install numpy pandas` without cache
- some repository level cache seems to be volatile 
- attempt to reduce vendors code in core
- drop black, mypi, and flake8
- sibling and path dependencies should have a profiles attribute 
- support pkm install -g, -ga and -ge env
- Installer should be made application level singleton and stateless
- package.all_requires - rename to package.dependencies