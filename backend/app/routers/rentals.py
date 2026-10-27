from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_active_user
from app.models import Rental, User
from app.schemas import DashboardOut, RentalOut, RentRequest
from app.services.rental import dashboard, rent_book, return_book, _rental_out

router = APIRouter(prefix="/rentals", tags=["rentals"])


@router.get("/me", response_model=DashboardOut)
def my_rentals(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return dashboard(db, user)


@router.post("", response_model=RentalOut, status_code=status.HTTP_201_CREATED)
def rent(
    body: RentRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rental = rent_book(db, user, body.book_id)
    rental = (
        db.query(Rental)
        .options(joinedload(Rental.book))
        .filter(Rental.id == rental.id)
        .one()
    )
    return _rental_out(rental)


@router.post("/{rental_id}/return", response_model=RentalOut)
def return_rental(
    rental_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rental = return_book(db, user, rental_id)
    rental = (
        db.query(Rental)
        .options(joinedload(Rental.book))
        .filter(Rental.id == rental.id)
        .one()
    )
    return _rental_out(rental)