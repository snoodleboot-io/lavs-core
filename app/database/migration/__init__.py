"""Idempotent startup migration from the legacy flat schema to the relational one.

The legacy LAVS schema stored every release as a row in a single ``Versions``
table keyed by ``product_name``. The P1 relational model splits this into
``products`` -> ``components`` -> ``versions``. :class:`FlatToRelationalMigration`
performs an inspect-then-migrate pass that is safe to run on every boot.
"""
