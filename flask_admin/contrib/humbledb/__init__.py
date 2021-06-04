# flake8: noqa
try:
    import humbledb
except ImportError:
    raise Exception('Please install humbledb in order to use humbledb integration')

from .view import ModelView
