After submitting to GitHub, GitHub security alerts reported that the NumPy
version in `requirements.txt` was too old.

The recommendation was to update NumPy to `>= 1.22`, because older versions
have known issues such as buffer overflow bugs and incorrect string comparison.

However, the `deep-forest` library requires `numpy < 1.20.0`, so this dependency
needs to be handled separately for environments that still rely on
`deep-forest`.
