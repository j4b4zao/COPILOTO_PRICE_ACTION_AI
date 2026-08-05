"""
core/registry.py
"""

from typing import Any


class Registry:
    """
    Registro central de módulos do sistema.
    """

    def __init__(self):
        self._modules: dict[str, Any] = {}

    def register(self, module):

        if not hasattr(module, "name"):
            raise AttributeError(
                f"{module.__class__.__name__} não possui atributo 'name'."
            )

        if module.name in self._modules:
            raise ValueError(
                f"Módulo '{module.name}' já registrado."
            )

        self._modules[module.name] = module

    def get(self, name):

        return self._modules.get(name)

    def exists(self, name):

        return name in self._modules

    def remove(self, name):

        self._modules.pop(name, None)

    def all(self):

        return list(self._modules.values())

    def clear(self):

        self._modules.clear()

    def __contains__(self, name):

        return name in self._modules

    def __len__(self):

        return len(self._modules)

    def __iter__(self):

        return iter(self._modules.values())