"""Cross-cutting security primitives: age encryption, signed tokens, principals.

These sit outside the domain (they touch crypto libraries and time) but are not
storage or transport either. The auth service composes them; the domain stays
pure.
"""
