# Contributing

## Setting Up A Development Environment

You can quickly set up a [Vagrant](https://www.vagrantup.com/)-based development environment by
cloning the [otm-vagrant](https://github.com/opentreemap/otm2-vagrant)
repository.

## Django and Python style

### Indentation

Four spaces. No tabs, please.

### Linting

We run all our our Python code (excluding migrations and settings)
through [flake8](https://flake8.readthedocs.org/en/2.2.3/). If you are
using the vagrant-based development setup, there is a
[fabric](http://www.fabfile.org/) task that will run flake8 with the
correct settings.

```
fab vagrant check
```

### Testing

We try to unit test as much of our code as possible.
If you are using the vagrant-based development setup, there is a task that will run the unit test suite.
Please run the unit tests before submitting a pull request if you modify Python code,

```
fab vagrant test
```

### View Functions

OpenTreeMap uses functional views rather than class-based views and
prefers nested calls rather than decorators, to simplify testing and
composability. Read through [decorators.py](https://github.com/OpenTreeMap/otm-core/blob/master/opentreemap/treemap/decorators.py)
file, and also the [django-tinsel project](https://github.com/azavea/django-tinsel) and it's `decorate` and `route` functions, which we use as the foundation of our composed view
functions. For a good example of how these functions are used,
reference [the treemap views module](https://github.com/OpenTreeMap/otm-core/blob/master/opentreemap/treemap/views/__init__.py)

### Templates

Nearly all of the markup for OpenTreeMap is generated by Django
templates, rather than client-side Javascript. If you are going to
create markup, we prefer that it is created via a Django template.

## Javascript Style and Patterns

### Indentation

Four spaces. No tabs, please.

### Modules

We use [browserify](http://browserify.org/) to compile nodejs-style
modules for use in the browser. If you are using the vagrant-based
development environment there is a fabric task that will compile a
Javascript bundle and collect all the static Django assets

```
fab vagrant static:dev_mode=True
```

### Bacon.js

We use [Bacon.js](http://baconjs.github.io/) to manage events in the
browser. Please reference the existing modules in the
[src](https://github.com/OpenTreeMap/otm-core/tree/master/opentreemap/treemap/js/src)
directory for examples of how we use stream processing rather than
directly attaching callbacks to DOM events.

### Testing

We have built a [mocha](http://visionmedia.github.io/mocha/)-based
unit test setup for our Javascript. The
[html test harness](https://github.com/OpenTreeMap/otm-core/blob/master/opentreemap/treemap/js/test/test.html)
handles finding and executing tests from any of the modules in the
[test directory](https://github.com/OpenTreeMap/otm-core/tree/master/opentreemap/treemap/js/test).
Individual tests are just functions exported from a module in the test
directory. You can open ``test.html`` to run the tests on demand, or
use [testem](https://github.com/airportyh/testem) to run the test
suite when files change.

## Architecture

This section addresses the question of where code should live.

### Permissions

Because of the complicated relationship of models associated with permission checking, permissions are centralized in a module, `treemap/lib/perms.py`, instead of added as methods to a class. Functions that check permissions should be written to accept a number of related types or type combinations and stored in this module. The private functions in this module should be responsible for walking the necessary relationships in order to check the permission properly.

