# Mendeley Code For Python

This repo implements the Mendeley API in Python. It also implements a client library. It will also implement library analysis code.

## Current Status ##

Jim is currently (Jan 2020) reworking the code to have 3 features before building out some of the planned features of this library.
1. Reworking API to have specified input parameters, rather than just relying on keyword arguments. The hope is that this helps with autocomplete options.
2. Making the local client library backend into a sqlite database, rather than a pandas dataframe. I was running into data consistency issues that I hope this will solve.
3. Supporting local changes that are synced at a later point in time. Currently all changes are sent to the server, and only exist locally after then pulling from the server.

The old version of this code can be found at:
https://github.com/ScholarTools/mendeley_python

## Motivation

The focus is on developing scripting access to my Mendeley data, particularly user data. As a simple example, one might wish to know which of their Mendeley entries are missing valid Pubmed IDs, and remedy this by adding them. Doing this would help to ensure higher quality meta data. As another example, one might wish to know which of the references from a paper they are reading are in their library or not. By writing code we can make a query to the API for this information.

Mendeley provides a [Python SDK](https://github.com/Mendeley/mendeley-python-sdk). This version is meant to provide tighter support (specifically integration of methods into response objects) for further analysis.  This version does not yet implement all available [API methods](https://api.mendeley.com/apidocs/docs) although they are slowly being added. Additionally, adding new methods is relatively straightforward.


## Current Plans

(as of May 30, 2016)

We are currently working on building in support for a reference retrieval program. Steps in this program include:

1. Retrieving references for a paper (via the pypub and reference_resolver repositories) **(August 2016 Edit: Done! See [reference_resolver](https://github.com/ScholarTools/reference_resolver))**
2. Determining which references are in the user library. **(August 2016 Edit: Done! See [Shrew](https://github.com/ScholarTools/shrew))**
3. Adding missing references (on demand) via a GUI along with the main file (article). **(August 2016 Edit: Done! See [Shrew](https://github.com/ScholarTools/shrew))**

## Getting Started

1. Copy `config_template.py` into a file `user_config.py` and fill in the appropriate values. This will require signing up for a [Mendeley API account](https://mix.mendeley.com/portal#/register). Importantly, the redirect API should be: **https://localhost**.
2. Your library can then be loaded as:

```python
from mendeley import client_library
c = client_library.UserLibrary()
#c.docs will contain a pandas dataframe of your library
```

##Contributing

We welcome contributions. If you are interested please email Jim.

