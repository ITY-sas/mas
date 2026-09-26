class LangGraph:
    def __init__(self):
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)

    def deliberate(self, brief):
        # Implementación simplificada del grafo de deliberación
        decision = {"content": f"Idea generated for {brief.content}"}
        return decision
