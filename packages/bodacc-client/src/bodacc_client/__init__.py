"""Client Python de l'API BODACC."""

from bodacc_client.client import BodaccClient, BodaccError, BodaccRateLimitError
from bodacc_client.models import Annonce

__all__ = ["Annonce", "BodaccClient", "BodaccError", "BodaccRateLimitError"]
