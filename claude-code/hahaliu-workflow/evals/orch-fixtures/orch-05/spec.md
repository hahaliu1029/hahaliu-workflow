# Spec: user lookup

`lookup_user(db, name)` (snake_case) MUST reject empty or non-string names with
`ValueError`, return `None` when no row matches, and close the connection before
returning.
