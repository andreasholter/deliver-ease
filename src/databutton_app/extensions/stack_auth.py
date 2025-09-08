from pydantic import BaseModel


class SecretRef(BaseModel):
    name: str


class StackAuthExtensionConfig(BaseModel):
    projectId: str
    publishableClientKey: str
    jwksUrl: str
    secretRefForSecretServerKey: SecretRef


def get_stack_auth_issuer(c: StackAuthExtensionConfig) -> str:
    return f"https://api.stack-auth.com/api/v1/projects/{c.projectId}"

# Project ID is the audience
def get_stack_auth_audience(c: StackAuthExtensionConfig) -> str:
    return c.projectId
