from fastapi import APIRouter
from enum import Enum


router = APIRouter(
    prefix="/examples",
    tags=["examples"],
)


class FoodOptions(str, Enum):
    chicken = "chicken"
    beef = "beef"
    fish = "fish"


@router.get("/")
async def root():
    return {"message": "Examples API"}


@router.get("/numbers/{number}")
async def read_number(number: int):
    return {"number": number}


@router.get("/options/{food_selection}")
async def get_food_selection(food_selection: FoodOptions):
    if food_selection is FoodOptions.chicken:
        return {"selection": food_selection, "message": "The chicken is 300 calories!"}

    if food_selection.value == "fish":
        return {"selection": food_selection, "message": "The fish is only 150 calories!"}

    return {"selection": food_selection, "message": "You don't want to know how many calories the beef has."}


@router.get("/files/{file_path:path}")
async def read_file(file_path: str):
    return {"file_path": file_path}
