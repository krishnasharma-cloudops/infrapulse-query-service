from pydantic import BaseModel, Field

class MetricInput(BaseModel):
    hostname: str = Field(min_length=1, max_length=120, pattern=r'^[a-zA-Z0-9._-]+$')
    region: str = Field(default='local', min_length=1, max_length=80)
    cpu: float = Field(ge=0, le=100, allow_inf_nan=False)
    memory: float = Field(ge=0, le=100, allow_inf_nan=False)
    disk: float = Field(ge=0, le=100, allow_inf_nan=False)
