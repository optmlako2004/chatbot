from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import (
    BILLET_STATUTS,
    RECLAMATION_STATUTS,
    RECLAMATION_TYPES,
    TRAJET_STATUTS,
    TRANSPORT_TYPES,
)


TransportType = Literal[*TRANSPORT_TYPES]
BilletStatut = Literal[*BILLET_STATUTS]
TrajetStatut = Literal[*TRAJET_STATUTS]
ReclamationType = Literal[*RECLAMATION_TYPES]
ReclamationStatut = Literal[*RECLAMATION_STATUTS]


class IdentityCheck(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    date_naissance: date


class TrajetOut(BaseModel):
    id: str
    type: TransportType
    depart: str
    arrivee: str
    date_depart: datetime
    date_arrivee: datetime
    compagnie: str
    prix: float
    places_dispo: int
    retard_minutes: int
    statut: TrajetStatut
    photo_url: Optional[str] = None
    has_wifi: bool = True
    has_prise: bool = True
    stops: str = "direct"
    classe: str = "Standard"
    # Vols avec escale(s)
    escales: list[str] = []          # ["New York JFK", "Miami MIA"]
    duree_escale_min: int = 0        # durée totale d'escale en minutes

    model_config = {"from_attributes": True}


class TrajetSearch(BaseModel):
    type: Optional[TransportType] = None
    depart: Optional[str] = None
    arrivee: Optional[str] = None
    date: Optional[date] = None
    passagers: int = Field(default=1, ge=1, le=10)


class UserCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    date_naissance: date
    email: EmailStr
    telephone: Optional[str] = Field(default=None, max_length=20)


class UserOut(BaseModel):
    id: str
    nom: str
    prenom: str
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class BilletCreate(BaseModel):
    trajet_id: str
    voyageur: UserCreate
    siege: Optional[str] = None
    prix_paye: Optional[float] = None
    classe: Optional[str] = None
    nb_places: Optional[int] = 1
    lang: Optional[str] = "fr"


class BilletOut(BaseModel):
    id: str
    numero_billet: str
    statut: BilletStatut
    siege: Optional[str]
    voiture: Optional[str] = None
    tarif: str = "Loisir"
    prix_paye: float
    created_at: datetime
    trajet: TrajetOut
    user: UserOut

    model_config = {"from_attributes": True}


class BilletAccess(BaseModel):
    """Accès à un billet sans login : numéro + vérification identité."""

    numero_billet: str
    identity: IdentityCheck


class BilletModification(BaseModel):
    nouveau_trajet_id: str


class ReclamationCreate(BaseModel):
    numero_billet: Optional[str] = None
    identity: IdentityCheck
    type: ReclamationType
    description: str = Field(min_length=10, max_length=2000)
    email_contact: EmailStr


class ReclamationOut(BaseModel):
    id: str
    numero_suivi: str
    type: ReclamationType
    description: str
    statut: ReclamationStatut
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatStart(BaseModel):
    session_token: Optional[str] = None
    lang: Optional[str] = "fr"


class ChatMessage(BaseModel):
    session_token: str
    message: str = Field(min_length=1, max_length=20000)
    lang: Optional[str] = "fr"


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    tool_used: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    session_token: str
    answer: str
    tools_used: list[str] = []
    message_id: str
    quick_replies: list[str] = []
    results: list[dict] = []


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminStats(BaseModel):
    total_users: int
    total_billets: int
    total_reclamations: int
    total_chat_sessions: int
    reclamations_en_attente: int
