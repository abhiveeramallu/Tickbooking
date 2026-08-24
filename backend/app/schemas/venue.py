from pydantic import BaseModel, ConfigDict, Field

from app.models.seat import SeatCategory


class VenueSeatBase(BaseModel):
    row_label: str = Field(min_length=1, max_length=16)
    seat_number: int = Field(ge=1)
    category: SeatCategory
    x_position: int = Field(ge=0)
    y_position: int = Field(ge=0)


class VenueSeatCreate(VenueSeatBase):
    pass


class VenueSeatUpdate(BaseModel):
    row_label: str | None = Field(default=None, min_length=1, max_length=16)
    seat_number: int | None = Field(default=None, ge=1)
    category: SeatCategory | None = None
    x_position: int | None = Field(default=None, ge=0)
    y_position: int | None = Field(default=None, ge=0)


class VenueSeatResponse(VenueSeatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class VenueBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    location: str = Field(min_length=2, max_length=255)


class VenueCreate(VenueBase):
    seats: list[VenueSeatCreate] = Field(default_factory=list)


class VenueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    location: str | None = Field(default=None, min_length=2, max_length=255)


class VenueResponse(VenueBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by: int
    seats: list[VenueSeatResponse] = Field(default_factory=list)

