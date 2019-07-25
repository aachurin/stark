<!--p align="center">
    <img src="https://raw.githubusercontent.com/aachurin/stark/master/docs/img/logo-???.png" alt="Stark" />
</p-->
<p align="center">
    <em>A smart Web API framework, for Python 3.</em>
</p>
<!--p align="center">
<a href="https://travis-ci.org/???/stark">
    <img src="https://travis-ci.org/???/stark.svg?branch=master" alt="Build Status">
</a>
<a href="https://codecov.io/gh/???/stark">
    <img src="https://codecov.io/gh/???/stark/branch/master/graph/badge.svg" alt="codecov">
</a>
<a href="https://pypi.python.org/pypi/stark">
    <img src="https://badge.fury.io/py/stark.svg" alt="Package version">
</a>
</p-->

---

**Stark documentation:** https://stark.github.com 📘

---

# Features

Why might you consider using API Star for your next Web API project?

* **Schema generation** - Support for automatically generating OpenAPI schemas.
* **Expressive** - Type annotated views, that make for expressive, testable code.
* **Performance** - Dynamic behaviour for determining how to run each view makes API Star incredibly efficient.
* **Throughput** - Support for asyncio allows for building high-throughput non-blocking applications.

---

# Quickstart

Install API Star:

```bash
$ pip3 install stark
```

Create a new project in `app.py`:

```python
from stark import App, Route


def welcome(name=None):
    if name is None:
        return {'message': 'Welcome to API Star!'}
    return {'message': 'Welcome to API Star, %s!' % name}


routes = [
    Route('/', method='GET', handler=welcome),
]

app = App(routes=routes)


if __name__ == '__main__':
    app.serve('127.0.0.1', 5000, debug=True)

```
Open `http://127.0.0.1:5000/docs/` in your browser.

![API documentation](https://raw.githubusercontent.com/aachurin/stark/master/docs/img/api-docs.png)

---
