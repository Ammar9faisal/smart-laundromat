
from fastapi import APIRouter, HTTPException
from app.database import supabase


router = APIRouter(    #setup router for machines
    prefix="/api/machines",
    tags=["Machines"]
)

@router.get("/") #define a GET endpoint to retrieve active machines
def get_machines():
    try:
        response = (
            supabase.table("machines")
            .select("*")
            .eq("active", True) #active machines only which are available for use
            .execute()
        )

        return response.data

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve machines"
        )
