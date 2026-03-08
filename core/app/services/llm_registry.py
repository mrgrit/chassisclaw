class LLMRegistry:
    def __init__(self):
        self.connections = {}
        self.role_bindings = {}

    def register_connection(self, conn_id: str, payload: dict) -> dict:
        self.connections[conn_id] = payload
        return payload

    def bind_role(self, role: str, conn_id: str) -> None:
        if conn_id not in self.connections:
            raise ValueError(f"unknown conn_id: {conn_id}")
        self.role_bindings[role] = conn_id

    def resolve_llm_conn_for_role(self, role: str, target_id: str | None = None) -> dict:
        conn_id = self.role_bindings.get(role)
        if not conn_id:
            raise ValueError(f"no llm bound for role={role}")
        return self.connections[conn_id]
