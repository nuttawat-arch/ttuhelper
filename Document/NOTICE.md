# Attribution / Notice

`ttuhelper` is a modified and expanded helper for running SN TalkBot Docker images.

The helper design and portions of the original shell-script implementation were derived from:

- **TTMediaBot Docker Helper** by MuhammadGagah
- Original repository: https://github.com/MuhammadGagah/ttmediabot-docker-helper
- License: MIT, Copyright (c) 2025 MuhammadGagah

The bot image managed by this helper is SN TalkBot. SN TalkBot also incorporates ideas and functionality inspired by TTMediaBot by gumerov-amir, but the helper repository does not vendor the TTMediaBot application source.

The old command name `tthelper` is intentionally not installed or aliased by this project. The new global command is `ttuhelper`, allowing the old helper and the new helper to coexist on the same Linux server.
