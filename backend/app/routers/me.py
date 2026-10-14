"""Minha conta: perfil, kits comprados e vínculo de logins."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..deps import current_user, rate_limit
from ..models import User
from ..schemas import FacebookIn, GoogleIn, LibraryItemOut, ProfileUpdateIn, UserOut
from ..services import accounts, orders, social

router = APIRouter(prefix="/me", tags=["Minha conta"])


@router.get("", response_model=UserOut, summary="Meus dados")
def me(user: User = Depends(current_user)):
    return accounts.user_out(user)


@router.patch("", response_model=UserOut, summary="Atualizar meu nome")
def update_me(body: ProfileUpdateIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.name = " ".join(body.name.split())
    db.commit()
    return accounts.user_out(user)


@router.get("/library", response_model=List[LibraryItemOut], summary="Kits que eu comprei (pedidos pagos)")
def library(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return orders.library(db, user)


@router.post("/link/google", response_model=UserOut, summary="Vincular minha conta do Google",
             dependencies=[Depends(rate_limit("social", 30, 600))])
def link_google(body: GoogleIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings),
                user: User = Depends(current_user)):
    return accounts.user_out(accounts.link_social(db, user, "google", social.verify_google_id_token(body.id_token, s)))


@router.post("/link/facebook", response_model=UserOut, summary="Vincular minha conta do Facebook",
             dependencies=[Depends(rate_limit("social", 30, 600))])
def link_facebook(body: FacebookIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings),
                  user: User = Depends(current_user)):
    info = social.verify_facebook_token(body.access_token, s)
    return accounts.user_out(accounts.link_social(db, user, "facebook", info))
