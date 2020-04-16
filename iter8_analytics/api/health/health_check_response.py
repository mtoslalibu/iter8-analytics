from pydantic import BaseModel, Field



class Iter8HealthCheck(BaseModel):
    status: str = Field("Ok", description="Current health status of iter8 analytics")
