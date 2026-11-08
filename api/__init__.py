"""XploClone API package."""

from .proxy_env import sanitise_no_proxy

# httpx (via huggingface_hub) crashes on bare-IPv6 NO_PROXY entries —
# see api/proxy_env.py. Sanitise at package import so every entry
# point (uvicorn, tests, scripts) gets a parseable environment.
sanitise_no_proxy()
