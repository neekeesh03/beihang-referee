# DOCX package audit

The DOCX inspector works at the Office Open XML package level. It counts tables, embedded media, embedded objects, comments, tracked insertions/deletions, footnotes/endnotes, external relationships, and Office Math objects. It also flags plain-text math patterns such as `R^2` that may indicate equations or statistical notation were not converted into proper OMML.

This is a structural diagnostic. It does not claim that every equation is semantically correct; equation/unit consistency remains a scientific review task.
