class LangGraph:
    def __init__(self):
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)

    def deliberate(self, idea):
        # Implementación simplificada del grafo de deliberación
        decision = {"content": f"Decision made for {idea.content}"}
        return decision
