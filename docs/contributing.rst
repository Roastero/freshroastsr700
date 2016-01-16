============
Contributing
============

Setting up a development environment
------------------------------------
::

    git clone git@github.com:Roastero/freshroastsr700.git
    cd freshroastsr700
    virtualenv venv -p python3
    source venv/bin/activate
    python setup.py develop

Running tests
--------------
This module uses tox to run tests and a code linter. Run the commands below in 
the base project directory to install everything needed and run tests on the 
freshroastsr700 module.

::

    pip install -r test-requirements.txt
    tox
