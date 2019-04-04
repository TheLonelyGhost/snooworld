=========
Snooworld
=========

A Reddit API client with strong typing and testability built-in.

Usage
-----

TODO


Development
-----------

First, install `Poetry`_ in your chosen manner, then setup your environment:

.. code-block:: bash

    $ poetry install
    $ poetry run pre-commit install --allow-missing-config --hook-type pre-commit
    $ poetry run pre-commit install --allow-missing-config --hook-type pre-push
    $ poetry run pre-commit install --allow-missing-config --hook-type commit-msg

.. _Poetry: https://poetry.eustace.io/

This should install everything you need to get started.

Testing looks like this:

.. code-block:: bash

    $ poetry run pytest --cov=snooworld


Roadmap
-------

- [x] User flair (read/write)
- [x] Inbox messages (read/write)
- [ ] Comment (read/reply)
- [ ] Post (read/reply)
- [ ] Post flair (read/write)
